from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ASSETS = REPO_ROOT / "app-assets"
INTERVIEW_KEY = "sk-interview-test-key-0001"
REVIEW_KEY = "sk-review-test-key-0002"


def valid_env() -> dict[str, str]:
    return {
        "MODEL_BASE_URL": "https://interview.example/v1",
        "MODEL_API_KEY": INTERVIEW_KEY,
        "MODEL_NAME": "interview-model",
        "REVIEW_MODEL_BASE_URL": "https://review.example/v1",
        "REVIEW_MODEL_API_KEY": REVIEW_KEY,
        "REVIEW_MODEL_NAME": "review-model",
        "DATABASE_URL": "postgresql://blueprint:blueprint@localhost:5432/blueprint",
        "SKIP_MODEL_CHECK": "true",
    }


@pytest.fixture
def env() -> dict[str, str]:
    return valid_env()
