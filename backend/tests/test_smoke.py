import os

os.environ["DATABASE_URL"] = "sqlite:///./test_neomint.db"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"  # unreachable -> exercises in-memory fallback

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_full_flow():
    with TestClient(app) as c:
        r = c.post("/api/auth/register", json={"email": "a@b.com", "password": "password123", "display_name": "Ann"})
        assert r.status_code == 201, r.text
        assert c.post("/api/auth/register", json={"email": "a@b.com", "password": "password123"}).status_code == 409
        assert c.post("/api/auth/login", json={"email": "a@b.com", "password": "wrong-pass"}).status_code == 401
        tok = c.post("/api/auth/login", json={"email": "a@b.com", "password": "password123"}).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}

        assert c.get("/api/portfolio").status_code == 401
        assert c.get("/api/auth/admin/users", headers=h).status_code == 403

        assert len(c.get("/api/market/stocks", headers=h).json()) >= 10
        q = c.get("/api/market/quote/aapl", headers=h).json()
        assert q["symbol"] == "AAPL"
        assert c.get("/api/market/quote/NOPE", headers=h).status_code == 404

        b = c.post("/api/trade/buy", json={"symbol": "AAPL", "shares": 10}, headers=h)
        assert b.status_code == 200, b.text
        assert c.post("/api/trade/buy", json={"symbol": "AAPL", "shares": 10_000}, headers=h).status_code == 400
        assert c.post("/api/trade/sell", json={"symbol": "AAPL", "shares": 99}, headers=h).status_code == 400
        s = c.post("/api/trade/sell", json={"symbol": "AAPL", "shares": 4}, headers=h)
        assert s.status_code == 200, s.text

        p = c.get("/api/portfolio", headers=h).json()
        assert p["holdings"][0]["quantity"] == 6
        assert abs(p["net_worth"] - 100000) < 5000

        ai = c.post("/api/ai/analyze-portfolio", headers=h).json()
        assert 0 <= ai["risk_score"] <= 100 and ai["suggestions"]

        slip = c.get(f"/api/reports/trade-slip/{b.json()['transaction_id']}", headers=h)
        assert slip.status_code == 200 and slip.content[:4] == b"%PDF"
        wk = c.get("/api/reports/weekly-statement", headers=h)
        assert wk.status_code == 200 and wk.content[:4] == b"%PDF"

        adm = c.post("/api/auth/login", json={"email": "admin@neomint.dev", "password": "ChangeMe123!"}).json()["access_token"]
        ah = {"Authorization": f"Bearer {adm}"}
        assert c.post("/api/admin/run-nightly-close", headers=ah).json()["snapshots"] == 1
        assert c.post("/api/admin/run-nightly-close", headers=ah).json()["snapshots"] == 1  # idempotent
        lb = c.get("/api/leaderboard", headers=h).json()
        assert lb[0]["rank"] == 1
        assert len(c.get("/api/portfolio/history", headers=h).json()) == 1
