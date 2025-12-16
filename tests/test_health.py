# Integration Tests - not mocked
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_root_endpoint():
    """
    Testing that test_root_endpoint returns correct structure
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ML Deployment Platform"
    assert data["version"] == "1.0.0"
    assert data["status"] == "operational"

def test_health_check_structure():
    """Test Health Endpoint returns required fields"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "models" in data
    assert "total_models" in data
    assert isinstance(data["models"], dict)
    assert data["total_models"] >= 1
    assert len(data["MODELS"]) == data["total_models"] 

def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

def test_list_models_endpoint():
    """Test Models Listing"""
    response = client.get("/models")
    # We get a list from /models
    assert response.status_code == 200
    assert isinstance(models, list)
    models = response.json()
    assert len(models) >= 1
    # assert models[0]["name"] == "mobilenet"
    assert "version" in models[0]
    assert "framework" in models[0]