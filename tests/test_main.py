import os
import sys
import tempfile
from types import SimpleNamespace
from pathlib import Path

os.environ["EDUMUSIC_API_DB"] = str(Path(tempfile.mkdtemp()) / "leaderboard.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


def test_health_ok():
    assert main.health() == {"status": "ok"}


def test_add_and_list_score(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "leaderboard.db"))
    monkeypatch.setattr(main, "_rate_limiter", lambda key: False)
    main.init_db()

    response = main.add_score(
        main.ScoreIn(game_id="Piano 1", name="Sàm", score=321),
        SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")),
    )

    assert response["game_id"] == "piano-1"
    assert response["name"] == "SAM"

    rows = main.list_scores(game_id="piano-1", period="all-time", limit=10)

    assert len(rows) == 1
    assert rows[0]["name"] == "SAM"
    assert rows[0]["score"] == 321
    assert rows[0]["ts"]


def test_rate_limited_uses_shared_limiter(monkeypatch):
    calls = []

    def fake_limiter(key):
        calls.append(key)
        return True

    monkeypatch.setattr(main, "_rate_limiter", fake_limiter)

    assert main.rate_limited("127.0.0.1") is True
    assert calls == ["127.0.0.1"]
