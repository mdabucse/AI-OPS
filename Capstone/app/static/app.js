const simulateButton = document.querySelector('#simulate-button');
const resetButton = document.querySelector('#reset-button');
const logsBody = document.querySelector('#logs-body');
const filter = document.querySelector('#log-filter');
let loadedLogs = [];
let currentRunId = null;

const wait = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function explainCall(title, data) {
  if (title === 'Start Day 2 simulation') {
    return `This starts one new Day 2 incident. The database pool is saturated, login P95 is ${data?.current_p95_seconds ?? 'high'} seconds, and an RCA approval is created.`;
  }
  if (title === 'Read application traces and logs') {
    return `These ${Array.isArray(data) ? data.length : 0} records are the raw application evidence. They show the login request duration and the database connection wait.`;
  }
  if (title === 'Read metrics and detection results' || title === 'Read final metrics') {
    return `These metrics connect the symptom to the cause: P95 is ${data?.current_p95_seconds ?? '—'} seconds, the pool is ${data?.active_connections ?? '—'} active out of ${data?.pool_max ?? '—'}, and ${data?.waiting_requests ?? '—'} requests are waiting.`;
  }
  if (title === 'Retrieve RAG runbooks') {
    return `The agent retrieved ${data?.results?.length ?? 0} local runbook document(s) to support its diagnosis and recommendation.`;
  }
  if (title === 'Read alert delivery') {
    return `This confirms whether the dynamic-threshold/anomaly alert was recorded and which notification channel was used.`;
  }
  if (title === 'Read governance trace' || title === 'Read final governance trace') {
    return `These records provide traceability: the actor, correlation ID, model/retrieval evidence, policy decision, and remediation history.`;
  }
  if (title === 'Reset database pool') {
    return `The persistent simulated pool was returned to ${data?.pool_size ?? 20} connections. The next login will again demonstrate the high-latency baseline.`;
  }
  if (title === 'Approve remediation') {
    return data?.remediation?.status === 'applied'
      ? `The human approval was accepted. The simulated pool increased from ${data.remediation.changes?.pool_max_before ?? '—'} to ${data.remediation.changes?.pool_max_after ?? '—'} connections, so the next login should be faster.`
      : 'The approval response did not apply a remediation change.';
  }
  if (title === 'Reject remediation') {
    return 'The human rejected the recommendation. No pool change was applied, and the incident state remains unchanged.';
  }
  return 'This JSON is the raw response for the current step in the RCA workflow.';
}

function showStep(step) {
  const element = document.querySelector(`[data-step="${step}"]`);
  if (element) element.hidden = false;
}

function hideAllSteps() {
  ['traces', 'metrics', 'rca', 'approval', 'audit', 'governance'].forEach((step) => {
    const element = document.querySelector(`[data-step="${step}"]`);
    if (element) element.hidden = true;
  });
}

function resetRunView() {
  currentRunId = null;
  hideAllSteps();
  document.querySelector('#raw-timeline').hidden = false;
  document.querySelector('#call-stream').innerHTML = '';
  document.querySelector('#approval-list').innerHTML = '<p id="no-approvals" class="muted">Approval will appear after all evidence is collected.</p>';
  document.querySelector('#governance-list').innerHTML = '<li class="muted">Governance records will appear after the workflow.</li>';
  document.querySelector('#audit-list').innerHTML = '<li class="muted">Current-run audit events will appear after the workflow.</li>';
}

async function callAndShow(title, method, path, options = {}) {
  const { explanation, ...fetchOptions } = options;
  const stream = document.querySelector('#call-stream');
  const callId = `call-${Date.now()}-${stream.children.length}`;
  stream.insertAdjacentHTML(
    'beforeend',
    `<article id="${callId}" class="api-call pending"><div class="call-header"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(method)} ${escapeHtml(path)}</span></div><p class="muted">Calling...</p></article>`,
  );
  const call = document.querySelector(`#${callId}`);
  try {
    const response = await fetch(path, { ...fetchOptions, method });
    const text = await response.text();
    let data;
    try { data = JSON.parse(text); } catch { data = { raw: text }; }
    call.classList.remove('pending');
    call.classList.add(response.ok ? 'success' : 'failure');
    call.innerHTML = `<div class="call-header"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(method)} ${escapeHtml(path)} · HTTP ${response.status}</span></div><pre class="raw-json">${escapeHtml(JSON.stringify(data, null, 2))}</pre><div class="json-explanation"><strong>Explanation:</strong> ${escapeHtml(explanation || explainCall(title, data))}</div>`;
    await wait(500);
    if (!response.ok) throw new Error(`${method} ${path} returned HTTP ${response.status}`);
    return data;
  } catch (error) {
    call.classList.remove('pending');
    call.classList.add('failure');
    call.innerHTML += `<p class="error">${escapeHtml(error.message)}</p>`;
    throw error;
  }
}

function applyMetrics(metrics) {
  document.querySelector('#current-p95').textContent = metrics.current_p95_seconds ?? '—';
  document.querySelector('#baseline-p95').textContent = metrics.baseline_p95_seconds ?? '—';
  document.querySelector('#dynamic-threshold').textContent = `Dynamic threshold: ${metrics.dynamic_threshold_seconds ?? '—'} seconds`;
  document.querySelector('#threshold-status').textContent = `Status: ${metrics.threshold_status ?? '—'}`;
  document.querySelector('#anomaly-status').textContent = metrics.anomaly_status ?? '—';
  document.querySelector('#anomaly-score').textContent = `Score: ${metrics.anomaly_score ?? '—'}`;
  document.querySelector('#alert-status').textContent = metrics.alert_status ?? '—';
  document.querySelector('#alert-channel').textContent = `Channel: ${metrics.alert_channel ?? '—'}`;
  document.querySelector('#pool-status').textContent = `${metrics.active_connections ?? '—'} / ${metrics.pool_max ?? '—'}`;
  document.querySelector('#waiting').textContent = metrics.waiting_requests ?? '—';
}

function updatePoolState(payload) {
  const poolSize = payload?.pool_size
    ?? payload?.pool_max
    ?? payload?.changes?.pool_max_after
    ?? payload?.remediation?.changes?.pool_max_after;
  if (poolSize == null) return;
  const label = Number(poolSize) > 20 ? 'expanded' : 'baseline/saturated';
  document.querySelector('#pool-state').textContent = `Current database pool: ${label} · ${poolSize} connections`;
}

function renderLogs() {
  const query = (filter.value || '').toLowerCase();
  const rows = loadedLogs.filter((log) => JSON.stringify(log).toLowerCase().includes(query));
  logsBody.innerHTML = rows.length
    ? rows.map((log) => `<tr><td>${log.level}</td><td>${log.endpoint}</td><td>${log.status}</td><td>${log.duration_ms} ms</td><td>${log.message}</td></tr>`).join('')
    : '<tr><td colspan="5" class="muted">No matching logs.</td></tr>';
}

function renderGovernance(records) {
  const markup = records.length
    ? records.map((record) => `<li><strong>${record.event_type}</strong><span>${record.actor} · ${record.policy_decision || 'recorded'} · ${record.correlation_id.slice(0, 8)}</span></li>`).join('')
    : '<li class="muted">No governance records yet.</li>';
  document.querySelector('#governance-list').innerHTML = markup;
  document.querySelector('#audit-list').innerHTML = markup;
}

function attachApprovalHandlers() {
  document.querySelectorAll('[data-action]').forEach((button) => {
    button.onclick = async () => {
      const approval = button.closest('[data-approval-id]');
      const action = button.dataset.action;
      try {
        button.disabled = true;
        const result = await callAndShow(
          `${action === 'approve' ? 'Approve' : 'Reject'} remediation`,
          'POST',
          `/api/approvals/${approval.dataset.approvalId}/${action}`,
        );
        approval.remove();
        if (!document.querySelector('#approval-list').children.length) {
          document.querySelector('#approval-list').innerHTML = '<p class="muted">Decision recorded for this run.</p>';
        }
        document.querySelector('#remediation-status').textContent = result.remediation?.status || action;
        updatePoolState(result);
        document.querySelector('#login-hint').textContent = action === 'approve'
          ? 'Pool increased. Log out and sign in again to see the lower login time.'
          : 'No pool change was made. Approve the recommendation to reduce the simulated login latency.';
        showStep('audit');
        showStep('governance');
        const metrics = await callAndShow('Read final metrics', 'GET', `/api/metrics?run_id=${currentRunId}`);
        applyMetrics(metrics);
        const governance = await callAndShow('Read final governance trace', 'GET', `/api/governance?run_id=${currentRunId}`);
        renderGovernance(governance);
      } catch (error) {
        console.error('Approval workflow failed', error);
      } finally {
        button.disabled = false;
      }
    };
  });
}

function renderApproval(payload) {
  if (!payload?.approval || payload.approval.status !== 'pending') return;
  const list = document.querySelector('#approval-list');
  const empty = document.querySelector('#no-approvals');
  if (empty) empty.remove();
  list.insertAdjacentHTML('afterbegin', `<article class="approval" data-approval-id="${payload.approval.approval_id}"><p class="muted">Approval ${payload.approval.approval_id.slice(0, 8)}</p><p>${payload.approval.requested_action}</p><button class="approve" data-action="approve">Approve</button><button class="secondary reject" data-action="reject">Reject</button></article>`);
  attachApprovalHandlers();
}

function renderRca(payload) {
  if (!payload?.rca) return;
  document.querySelector('#rca-root-cause').textContent = payload.rca.root_cause;
  document.querySelector('#rca-recommendation').textContent = `Recommendation: ${payload.rca.recommendation}`;
  document.querySelector('#rca-evidence').innerHTML = payload.rca.evidence.map((item) => `<li>${item}</li>`).join('');
  document.querySelector('#rag-sources').innerHTML = (payload.rca.retrieved_context || []).map((source) => `<li><strong>${source.title}</strong><br><span class="muted">${source.content}</span></li>`).join('') || '<li class="muted">No RAG context loaded.</li>';
  const approvalStatus = payload.approval?.status || 'pending';
  document.querySelector('#remediation-status').textContent = payload.approval?.remediation?.status || (approvalStatus === 'approved' ? 'applied' : 'waiting');
}

simulateButton?.addEventListener('click', async () => {
  simulateButton.disabled = true;
  simulateButton.textContent = 'Simulating...';
  resetRunView();
  try {
    const run = await callAndShow('Start Day 2 simulation', 'POST', '/api/simulations/day2/start');
    currentRunId = run.run_id;
    const logs = await callAndShow('Read application traces and logs', 'GET', `/api/logs?run_id=${run.run_id}`);
    const metrics = await callAndShow('Read metrics and detection results', 'GET', `/api/metrics?run_id=${run.run_id}`);
    await callAndShow('Retrieve RAG runbooks', 'GET', `/api/rag/search?q=${encodeURIComponent('database connection pool login latency')}&top_k=2`);
    await callAndShow('Read alert delivery', 'GET', `/api/alerts?run_id=${run.run_id}`);
    const governance = await callAndShow('Read governance trace', 'GET', `/api/governance?run_id=${run.run_id}`);
    applyMetrics(metrics);
    updatePoolState(run);
    loadedLogs = logs;
    renderLogs();
    renderGovernance(governance);
    document.querySelector('#run-label').textContent = `Run ${run.run_id} · correlation ${run.correlation_id}`;
    showStep('traces');
    showStep('metrics');
    showStep('rca');
    renderRca(run);
    showStep('approval');
    renderApproval(run);
  } catch (error) {
    console.error('Simulation workflow failed', error);
  } finally {
    simulateButton.disabled = false;
    simulateButton.textContent = 'Run RCA simulation';
  }
});

resetButton?.addEventListener('click', async () => {
  resetButton.disabled = true;
  resetButton.textContent = 'Resetting...';
  resetRunView();
  try {
    const result = await callAndShow('Reset database pool', 'POST', '/api/simulations/reset');
    updatePoolState(result);
    document.querySelector('#login-hint').textContent = 'Pool reset to baseline. Log out and sign in again to reproduce the high login time.';
  } catch (error) {
    console.error('Reset workflow failed', error);
  } finally {
    resetButton.disabled = false;
    resetButton.textContent = 'Reset pool';
  }
});

filter?.addEventListener('input', renderLogs);
