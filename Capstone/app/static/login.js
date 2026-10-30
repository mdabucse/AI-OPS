const loginForm = document.querySelector('#login-form');
const loginTiming = document.querySelector('#login-timing');
const loginButton = document.querySelector('#login-button');

loginForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const startedAt = performance.now();
  loginButton.disabled = true;
  loginButton.textContent = 'Signing in...';
  loginTiming.textContent = 'Login time: measuring...';

  try {
    const response = await fetch(loginForm.action, {
      method: 'POST',
      body: new FormData(loginForm),
      credentials: 'same-origin',
    });
    const elapsedMs = Math.round((performance.now() - startedAt) * 100) / 100;
    loginTiming.textContent = `Login time: ${elapsedMs} ms`;
    if (response.ok || response.redirected) {
      await new Promise((resolve) => window.setTimeout(resolve, 800));
      window.location.assign(response.url || '/dashboard');
    } else {
      loginButton.disabled = false;
      loginButton.textContent = 'Sign in';
    }
  } catch (error) {
    loginTiming.textContent = 'Login time: unavailable';
    loginButton.disabled = false;
    loginButton.textContent = 'Sign in';
  }
});
