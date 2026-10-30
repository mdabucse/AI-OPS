from types import SimpleNamespace

from app import alerting
from app.db import SessionLocal, init_db
from app.models import AlertEvent
from app.simulation import start_login_scenario


def test_simulation_creates_local_teams_alert():
    init_db()
    with SessionLocal() as session:
        run = start_login_scenario(session, actor="admin")
        alert = session.query(AlertEvent).filter_by(run_id=run.id).one()

        assert alert.channel == "teams"
        assert alert.status == "simulated"
        assert "1.35" in alert.payload["text"]


def test_teams_webhook_success_is_recorded(monkeypatch):
    init_db()
    with SessionLocal() as session:
        run = start_login_scenario(session, actor="admin")
        sent = {}

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout):
            sent["body"] = request.data.decode("utf-8")
            sent["timeout"] = timeout
            return Response()

        monkeypatch.setattr(alerting, "settings", SimpleNamespace(teams_webhook_url="https://teams.example/webhook"))
        monkeypatch.setattr(alerting, "urlopen", fake_urlopen)
        alert = alerting.send_alert(session, run.id, channel="teams")

        assert alert.status == "sent"
        assert "AIOps RCA alert" in sent["body"]


def test_failed_webhook_is_not_reported_as_sent(monkeypatch):
    init_db()
    with SessionLocal() as session:
        run = start_login_scenario(session, actor="admin")
        monkeypatch.setattr(alerting, "settings", SimpleNamespace(teams_webhook_url="https://teams.example/webhook"))
        monkeypatch.setattr(alerting, "urlopen", lambda request, timeout: (_ for _ in ()).throw(OSError("network down")))

        alert = alerting.send_alert(session, run.id, channel="teams")

        assert alert.status == "failed"
        assert alert.error == "network down"
