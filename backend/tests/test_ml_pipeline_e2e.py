import pytest
import os
import io
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base
import app.models as models
from unittest.mock import patch, MagicMock


# Setup test database
@pytest.fixture
def db_engine_e2e():
    """Create a file-based SQLite database for E2E tests."""
    db_file = "test_e2e.db"
    if os.path.exists(db_file):
        os.remove(db_file)
    engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}
    )
    # Import all models to ensure they are registered with Base
    import app.models

    Base.metadata.create_all(engine)
    yield engine
    # Cleanup
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass


@pytest.fixture
def db_session_e2e(db_engine_e2e):
    """Create a database session for E2E testing."""
    SessionLocal = sessionmaker(bind=db_engine_e2e)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db_session_e2e):
    def override_get_db():
        yield db_session_e2e

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_ml_pipeline_e2e(client, db_session_e2e: Session):
    """
    End-to-End test for the ML pipeline:
    Replay Upload -> Feature Extraction -> ML Prediction -> SHAP Explanation -> Build Order Category
    """
    # 1. Prepare a real replay file for upload
    # Try multiple possible locations for replays
    possible_paths = ["replays", "backend/replays", "../backend/replays"]
    replay_dir = None
    for p in possible_paths:
        if os.path.exists(p) and os.path.isdir(p):
            replay_dir = p
            break

    if not replay_dir:
        pytest.skip(f"Replays directory not found. Checked: {possible_paths}")

    replays = [f for f in os.listdir(replay_dir) if f.endswith(".SC2Replay")]
    if not replays:
        pytest.skip(f"No replay files found in {replay_dir}")

    # Try multiple replays until one passes winner determination
    success = False
    last_error = None
    match_id = None

    # Sort replays to be deterministic
    replays.sort()

    # Mock the predictor to return SHAP impacts since we don't have a trained model
    mock_shap_impacts = [
        {"feature": "mmr_diff", "impact": 0.5, "magnitude": 0.5},
        {"feature": "combat_diff", "impact": -0.2, "magnitude": 0.2},
        {"feature": "economic_diff", "impact": 0.3, "magnitude": 0.3},
    ]

    # We need to mock it throughout the test
    with patch("app.services.ml_predictor.MLPredictor.predict") as mock_predict:
        mock_predict.return_value = {
            "predicted_winner": 1,
            "team_1_win_probability": 65.0,
            "team_2_win_probability": 35.0,
            "confidence": "Medium",
            "model": "MLPredictor (Mocked)",
            "key_factors": ["Team 1 has better MMR"],
            "shap_impacts": mock_shap_impacts,
        }

        for replay_filename in replays[:10]:  # Try first 10 replays
            replay_path = os.path.join(replay_dir, replay_filename)

            with open(replay_path, "rb") as f:
                replay_content = f.read()

            # 2. Upload the replay
            response = client.post(
                "/replays/upload",
                files={
                    "file": (
                        replay_filename,
                        io.BytesIO(replay_content),
                        "application/octet-stream",
                    )
                },
            )

            if response.status_code == 200:
                success = True
                data = response.json()
                match_id = data["match_id"]
                print(f"Successfully uploaded {replay_filename}, match_id={match_id}")
                break
            else:
                try:
                    last_error = response.json().get("detail", "Unknown error")
                except:
                    last_error = response.text
                print(f"Skipping {replay_filename}: {last_error}")
                continue

        if not success:
            pytest.fail(f"Failed to upload any replay. Last error: {last_error}")

        # 3. Verify Feature Extraction in DB
        # Check if PerformanceFeatures were created
        perf_features = (
            db_session_e2e.query(models.PerformanceFeatures)
            .join(models.MatchPlayer)
            .filter(models.MatchPlayer.match_id == match_id)
            .all()
        )

        assert len(perf_features) > 0, (
            "Performance features should be extracted for players"
        )

        # Verify Build Order Category is assigned (FR-4)
        has_build_type = any(pf.detected_build_type is not None for pf in perf_features)
        assert has_build_type, "At least one player should have a detected build type"

        # Check if build_order_json is populated
        has_build_order = any(pf.build_order_json is not None for pf in perf_features)
        assert has_build_order, "Build order JSON should be populated"

        # 4. Verify SHAP Explanation via API
        commentary_response = client.get(f"/replays/matches/{match_id}/commentary")
        assert commentary_response.status_code == 200
        commentary_data = commentary_response.json()

        assert "shap_impacts" in commentary_data
        assert len(commentary_data["shap_impacts"]) > 0
        assert commentary_data["shap_impacts"][0]["feature"] == "mmr_diff"

        # 5. Verify Build Order Category values
        for pf in perf_features:
            if pf.detected_build_type:
                assert pf.detected_build_type in [
                    "rush",
                    "macro",
                    "timing",
                    "cheese",
                    "unknown",
                ]

    print(f"E2E ML Pipeline test passed for match {match_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
