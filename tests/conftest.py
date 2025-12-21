import pytest
from unittest.mock import MagicMock, patch
import sys

# Mock MLflow BEFORE importing src.main
mock_mlflow = MagicMock()
sys.modules['mlflow'] = mock_mlflow
sys.modules['mlflow.tensorflow'] = MagicMock()
sys.modules['mlflow.tracking'] = MagicMock()

# Mock TensorFlow Hub
mock_tf_hub = MagicMock()
sys.modules['tensorflow_hub'] = mock_tf_hub

# NOW safe to import
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Provide test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_mlflow_env(monkeypatch):
    """Mock MLflow environment variables"""
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")