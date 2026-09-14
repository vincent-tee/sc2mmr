"""
Tests for organizer pre-game judgments and post-game feedback
(app/api/judgments.py, app/models.py PregameJudgment/PostgameFeedback).

These are purely additive/observational records: the key invariants under
test are (1) the pre-game estimate locks and becomes immutable, (2)
post-game feedback is a genuinely separate record, never merged into the
judgment row, and (3) none of this ever touches a player's rating.
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import GameMode, Match, Player


@pytest.mark.parametrize("override", [
    {"team1_player_ids": [1, 1]}, {"team2_player_ids": [1, 3]},
    {"team1_player_ids": [999, 2]}, {"human_win_prob": 1.01},
    {"model_predicted_team1_win_prob": -0.1}, {"author": "   "},
    {"team1_context": [{"player_id": 3, "race": "Terran"}]},
])
def test_invalid_judgments_rejected(client, override):
    assert client.post('/judgments', json=judgment_payload(**override)).status_code == 422


@pytest.mark.parametrize("field", ["confidence", "reason", "human_estimate"])
def test_explicit_null_edits_rejected(client, field):
    jid = client.post('/judgments', json=judgment_payload()).json()['id']
    assert client.patch(f'/judgments/{jid}', json={field: None}).status_code == 422


def test_private_reads_in_public_read_mode(client, monkeypatch):
    monkeypatch.setattr(settings, 'auth_enabled', True)
    monkeypatch.setattr(settings, 'auth_public_read', True)
    for url in ['/judgments', '/judgments/feedback/list', '/judgments/selections/calibration']:
        assert client.get(url).status_code == 401


def make_prediction(db_engine, rank=2):
    from app.services.balance_capture import BalancePredictionService
    with Session(db_engine) as db:
        prediction = BalancePredictionService.record_suggestion(
            db, 'mmr_v2', rank, [1, 2], [3, 4], .65,
            features={'map_name': 'Goldenaura LE',
                      'ratings': {str(i): {'mu': 20 + i * 3, 'sigma': 4} for i in range(1, 5)}},
        )
        db.commit()
        return prediction.id


def make_played_match(db_engine, start, flipped=False):
    from datetime import timedelta
    from app.models import MatchPlayer, Race
    with Session(db_engine) as db:
        match = Match(played_at=start + timedelta(minutes=1), game_mode=GameMode.TWO_V_TWO,
                      map_name='Goldenaura LE', duration_seconds=600)
        db.add(match); db.flush()
        for pid in range(1, 5):
            team = (2 if pid <= 2 else 1) if flipped else (1 if pid <= 2 else 2)
            db.add(MatchPlayer(match_id=match.id, player_id=pid, team_number=team,
                               race=Race.TERRAN, won=pid <= 2, mu_before=25,
                               sigma_before=8, mu_after=25, sigma_after=8))
        db.commit()
        return match.id


def test_selection_links_flipped_match_and_scores_selected_lower_rank(client, db_engine):
    from app.models import BalanceSelection
    prediction_id = make_prediction(db_engine)
    payload = judgment_payload(balance_prediction_id=prediction_id, model_predicted_team1_win_prob=.01)
    judgment = client.post('/judgments', json=payload).json()
    assert judgment['model_predicted_team1_win_prob'] == .65  # server owns model snapshot
    locked = client.post(f"/judgments/{judgment['id']}/lock").json()
    assert locked['selection_id'] is not None
    assert client.post(f"/judgments/{judgment['id']}/lock").json()['selection_id'] == locked['selection_id']
    start = datetime.fromisoformat(locked['locked_at'])
    match_id = make_played_match(db_engine, start, flipped=True)
    candidates = client.get(f'/judgments/selections/candidates/{match_id}').json()
    assert [c['id'] for c in candidates] == [locked['selection_id']]
    link = f"/judgments/selections/{locked['selection_id']}/match/{match_id}"
    assert client.post(link).status_code == 200
    assert client.post(link).status_code == 200  # idempotent
    linked = client.get('/judgments', params={'match_id': match_id}).json()
    assert linked[0]['id'] == judgment['id']
    stats = client.get('/judgments/selections/calibration').json()
    assert stats['models']['mmr_v2']['count'] == 1
    assert stats['models']['mmr_v2']['brier_score'] == pytest.approx(.1225)
    with Session(db_engine) as db:
        assert db.get(BalanceSelection, locked['selection_id']).team1_won == 1
    second = make_played_match(db_engine, start)
    assert client.post(f"/judgments/selections/{locked['selection_id']}/match/{second}").status_code == 409


def test_swaps_recompute_snapshot_and_never_change_player_ratings(client, db_engine):
    prediction_id = make_prediction(db_engine)
    response = client.post('/judgments', json=judgment_payload(
        balance_prediction_id=prediction_id, team1_player_ids=[1, 3], team2_player_ids=[2, 4],
        team1_context=None, team2_context=None,
    ))
    assert response.status_code == 200
    probability = response.json()['model_predicted_team1_win_prob']
    assert 0 < probability < .5
    with Session(db_engine) as db:
        assert all(p.mu == 25 for p in db.query(Player))


def test_balance_response_returns_persisted_prediction_ids(client, db_engine):
    from app.models import BalancePrediction
    response = client.post('/teams/balance', json={'player_ids': [1, 2, 3, 4], 'top_n': 3})
    assert response.status_code == 200, response.text
    ids = [s['balance_prediction_id'] for s in response.json()]
    assert len(ids) == len(set(ids)) == 3
    with Session(db_engine) as db:
        assert db.query(BalancePrediction).filter(BalancePrediction.id.in_(ids)).count() == 3


def test_two_drafts_cannot_start_same_suggestion_twice(client, db_engine):
    from app.models import BalanceSelection
    prediction_id = make_prediction(db_engine)
    drafts = [client.post('/judgments', json=judgment_payload(balance_prediction_id=prediction_id)).json()
              for _ in range(2)]
    assert client.post(f"/judgments/{drafts[0]['id']}/lock").status_code == 200
    assert client.post(f"/judgments/{drafts[1]['id']}/lock").status_code == 409
    assert not client.get(f"/judgments/{drafts[1]['id']}").json()['is_locked']
    with Session(db_engine) as db:
        assert db.query(BalanceSelection).count() == 1


def test_late_upload_cannot_consume_fresh_prediction(client, db_engine):
    from datetime import timedelta
    from app.models import BalancePrediction
    from app.services.balance_capture import BalancePredictionService
    prediction_id = make_prediction(db_engine)
    match_id = make_played_match(db_engine, datetime.utcnow() - timedelta(hours=1))
    with Session(db_engine) as db:
        BalancePredictionService.resolve_for_match(db, db.get(Match, match_id))
        assert not db.get(BalancePrediction, prediction_id).resolved


def test_stale_edit_cannot_overwrite_locked_judgment(client, db_engine):
    from fastapi import HTTPException
    from app.models import PregameJudgment
    from app.api.judgments import update_judgment, UpdateJudgmentRequest
    judgment = client.post('/judgments', json=judgment_payload()).json()
    with Session(db_engine) as stale:
        cached = stale.get(PregameJudgment, judgment['id'])
        assert not cached.is_locked
        assert client.post(f"/judgments/{judgment['id']}/lock").status_code == 200
        with pytest.raises(HTTPException) as exc:
            update_judgment(judgment['id'], UpdateJudgmentRequest(confidence='high'), stale)
        assert exc.value.status_code == 409
    assert client.get(f"/judgments/{judgment['id']}").json()['confidence'] == 'medium'


def test_feedback_cannot_mix_unrelated_links(client, real_match_id):
    judgment = client.post('/judgments', json=judgment_payload()).json()
    response = client.post('/judgments/feedback', json={
        'judgment_id': judgment['id'], 'match_id': real_match_id,
        'feedback': 'one_sided', 'author': 'Organizer',
    })
    assert response.status_code == 422


@pytest.fixture
def client(db_engine):
    with Session(db_engine) as db:
        db.add_all(
            Player(name=name, mu=25.0, sigma=8.333)
            for name in ("Alice", "Bob", "Carol", "Dave")
        )
        db.commit()

    def get_test_db():
        with Session(db_engine) as db:
            yield db

    app.dependency_overrides[get_db] = get_test_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def real_match_id(db_engine):
    """A real Match row's id, for tests exercising the match_id FK (which is
    enforced - a judgment/feedback row can't point at a match that doesn't
    exist, even though the column is nullable)."""
    with Session(db_engine) as db:
        match = Match(
            played_at=datetime.utcnow(),
            game_mode=GameMode.TWO_V_TWO,
            map_name="Goldenaura LE",
            duration_seconds=600,
        )
        db.add(match)
        db.commit()
        db.refresh(match)
        return match.id


def judgment_payload(**overrides):
    payload = {
        "team1_player_ids": [1, 2],
        "team2_player_ids": [3, 4],
        "map_name": "Goldenaura LE",
        "team1_context": [
            {"player_id": 1, "race": "Terran"},
            {"player_id": 2, "race": "Zerg"},
        ],
        "team2_context": [
            {"player_id": 3, "race": "Protoss"},
            {"player_id": 4, "race": "Terran"},
        ],
        "model_version": "mmr_v1",
        "model_predicted_team1_win_prob": 0.55,
        "human_estimate": "team1_favored",
        "human_win_prob": 0.65,
        "confidence": "medium",
        "reason": "current_form",
        "reason_note": "Bob has been on a tear lately",
        "author": "OrganizerName",
    }
    payload.update(overrides)
    return payload


def test_create_judgment_snapshots_roster_and_model_estimate(client):
    resp = client.post("/judgments", json=judgment_payload())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["team1_player_ids_key"] == "1,2"
    assert body["team2_player_ids_key"] == "3,4"
    assert body["model_version"] == "mmr_v1"
    assert body["model_predicted_team1_win_prob"] == 0.55
    assert body["human_estimate"] == "team1_favored"
    assert body["is_locked"] is False
    assert body["locked_at"] is None


def test_lock_prevents_further_edits(client):
    created = client.post("/judgments", json=judgment_payload()).json()
    jid = created["id"]

    patched = client.patch(f"/judgments/{jid}", json={"confidence": "high"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["confidence"] == "high"

    locked = client.post(f"/judgments/{jid}/lock")
    assert locked.status_code == 200
    assert locked.json()["is_locked"] is True
    assert locked.json()["locked_at"] is not None

    rejected = client.patch(f"/judgments/{jid}", json={"confidence": "low"})
    assert rejected.status_code == 409

    unchanged = client.get(f"/judgments/{jid}").json()
    assert unchanged["confidence"] == "high"


def test_lock_is_idempotent(client):
    jid = client.post("/judgments", json=judgment_payload()).json()["id"]
    first = client.post(f"/judgments/{jid}/lock").json()
    second = client.post(f"/judgments/{jid}/lock").json()
    assert first["locked_at"] == second["locked_at"]


def test_completed_match_cannot_receive_new_pregame_prediction(client, real_match_id):
    response = client.post("/judgments", json=judgment_payload(match_id=real_match_id))
    assert response.status_code == 409
    assert client.get("/judgments", params={"match_id": real_match_id}).json() == []


def test_postgame_feedback_is_a_separate_record(client):
    jid = client.post("/judgments", json=judgment_payload()).json()["id"]

    resp = client.post(
        "/judgments/feedback",
        json={
            "judgment_id": jid,
            "feedback": "snowballed_early",
            "note": "Team 1 stomped after a bad opening engagement",
            "author": "OrganizerName",
        },
    )
    assert resp.status_code == 200, resp.text
    feedback = resp.json()
    assert feedback["judgment_id"] == jid
    assert feedback["feedback"] == "snowballed_early"

    judgment = client.get(f"/judgments/{jid}").json()
    assert "feedback" not in judgment

    listed = client.get("/judgments/feedback/list", params={"judgment_id": jid}).json()
    assert len(listed) == 1
    assert listed[0]["id"] == feedback["id"]


def test_feedback_can_link_by_match_id_alone(client, real_match_id):
    resp = client.post(
        "/judgments/feedback",
        json={"match_id": real_match_id, "feedback": "disconnect", "author": "OrganizerName"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["judgment_id"] is None
    assert resp.json()["match_id"] == real_match_id


def test_feedback_requires_a_linkage_field(client):
    resp = client.post(
        "/judgments/feedback", json={"feedback": "other", "author": "OrganizerName"}
    )
    assert resp.status_code == 400


def test_feedback_rejects_unknown_judgment(client):
    resp = client.post(
        "/judgments/feedback",
        json={"judgment_id": 9999, "feedback": "other", "author": "OrganizerName"},
    )
    assert resp.status_code == 404


def test_feedback_rejects_unknown_match(client):
    resp = client.post(
        "/judgments/feedback",
        json={"match_id": 9999, "feedback": "other", "author": "OrganizerName"},
    )
    assert resp.status_code == 404


def test_create_judgment_rejects_unknown_match(client):
    resp = client.post("/judgments", json=judgment_payload(match_id=9999))
    assert resp.status_code == 404


def test_create_judgment_rejects_unknown_balance_prediction(client):
    resp = client.post("/judgments", json=judgment_payload(balance_prediction_id=9999))
    assert resp.status_code == 404


def test_judgment_and_feedback_never_touch_ratings(client, db_engine):
    with Session(db_engine) as db:
        before = {p.name: (p.mu, p.sigma, p.mmr) for p in db.query(Player).all()}

    jid = client.post("/judgments", json=judgment_payload()).json()["id"]
    client.patch(f"/judgments/{jid}", json={"confidence": "high"})
    client.post(f"/judgments/{jid}/lock")
    client.post(
        "/judgments/feedback",
        json={"judgment_id": jid, "feedback": "felt_balanced", "author": "OrganizerName"},
    )

    with Session(db_engine) as db:
        after = {p.name: (p.mu, p.sigma, p.mmr) for p in db.query(Player).all()}

    assert before == after


class TestAdminGating:
    """Write endpoints require the admin token (mirroring POST /players/aliases);
    reads stay on the standard session gate like every other GET endpoint."""

    @pytest.fixture
    def admin_token_on(self):
        saved = settings.admin_token
        settings.admin_token = "admin-secret"
        yield
        settings.admin_token = saved

    def test_create_rejected_without_admin_token(self, client, admin_token_on):
        resp = client.post("/judgments", json=judgment_payload())
        assert resp.status_code == 403

    def test_create_allowed_with_admin_token(self, client, admin_token_on):
        resp = client.post(
            "/judgments",
            json=judgment_payload(),
            headers={"X-Admin-Token": "admin-secret"},
        )
        assert resp.status_code == 200

    def test_lock_rejected_without_admin_token(self, client, admin_token_on):
        jid = client.post(
            "/judgments",
            json=judgment_payload(),
            headers={"X-Admin-Token": "admin-secret"},
        ).json()["id"]
        resp = client.post(f"/judgments/{jid}/lock")
        assert resp.status_code == 403

    def test_feedback_rejected_without_admin_token(self, client, admin_token_on):
        resp = client.post(
            "/judgments/feedback",
            json={"match_id": 1, "feedback": "other", "author": "Organizer"},
        )
        assert resp.status_code == 403

    def test_read_does_not_require_admin_token(self, client, admin_token_on):
        created = client.post(
            "/judgments",
            json=judgment_payload(),
            headers={"X-Admin-Token": "admin-secret"},
        ).json()
        resp = client.get(f"/judgments/{created['id']}")
        assert resp.status_code == 200
