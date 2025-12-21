import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client):
    """Test root endpoint returns correct structure"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ML Deployment Platform"
    assert data["version"] == "1.0.0"
    assert data["status"] == "operational"


def test_health_check_structure(client):
    """Test health endpoint returns required fields"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert "models" in data
    assert "total_models" in data
    assert isinstance(data["models"], dict)
    assert data["total_models"] >= 1
    assert len(data["models"]) == data["total_models"]


def test_metrics_endpoint(client):
    """Test Prometheus metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_list_models_endpoint(client):
    """Test models listing"""
    response = client.get("/models")
    assert response.status_code == 200
    models = response.json()
    assert len(models) >= 1
    # Check structure of first model
    first_model = models[0]
    assert "name" in first_model
    assert "version" in first_model
    assert "framework" in first_model
    assert "type" in first_model
    assert "status" in first_model