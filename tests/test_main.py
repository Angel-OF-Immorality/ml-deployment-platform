# mocked business logic
# We check code logic, business logic
# Infra and Static Configs are not tested here
import pytest
from unittest.mock import patch, MagicMock
import io
from PIL import Image
import tensorflow as tf


def create_test_image():
    """Helper fn to create test img"""
    img = Image.new('RGB', (224, 224), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes


def test_predict_model_not_found(client):
    """Test pred with non-existent models"""
    response = client.post(
        "/predict/nonexistent",
        files={"file": ("test.jpg", create_test_image(), "image/jpeg")}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@patch('src.main.loaded_models', {})  # Empty dict = not loaded
def test_predict_model_not_loaded(client):
    """Test model loading when model doesn't exist"""
    response = client.post(
        "/predict/mobilenet",
        files={"file": ("test.jpg", create_test_image(), "image/jpeg")}
    )
    assert response.status_code == 503
    assert "not loaded" in response.json()["detail"]


@patch('src.main.loaded_models')
@patch('src.main.mlflow.start_run')
@patch('src.main.mlflow.log_param')
@patch('src.main.mlflow.log_metric')
@patch('src.main.mlflow.set_tag')
@patch('src.main.tf.nn.softmax')
@patch('src.main.tf.nn.top_k')
def test_predict_success(mock_top_k, mock_softmax, mock_set_tag, mock_log_metric,
                         mock_log_param, mock_start_run, mock_loaded_models, client):
    """Mock Model Successful Prediction Test"""
    
    # MLflow context manager
    mock_start_run.return_value.__enter__.return_value = None
    mock_start_run.return_value.__exit__.return_value = None
    
    # Model is loaded
    mock_loaded_models.__contains__ = MagicMock(return_value=True)
    
    # Mock model prediction
    mock_model = MagicMock()
    fake_logits = tf.constant([[0.1, 0.8, 0.05, 0.03, 0.02]], dtype=tf.float32)
    mock_model.return_value = fake_logits
    mock_loaded_models.__getitem__ = MagicMock(return_value=mock_model)
    
    # Mock TensorFlow operations
    mock_softmax.return_value = fake_logits
    
    # Create mock top_k result
    mock_top_k_result = MagicMock()
    # Mock indices and values as TensorFlow-like objects
    mock_indices = MagicMock()
    mock_indices.__getitem__ = MagicMock(return_value=[
        MagicMock(numpy=MagicMock(return_value=i)) for i in [1, 0, 2, 3, 4]
    ])
    mock_values = MagicMock()
    mock_values.__getitem__ = MagicMock(return_value=[
        MagicMock(numpy=MagicMock(return_value=v)) for v in [0.8, 0.1, 0.05, 0.03, 0.02]
    ])
    mock_top_k_result.indices = mock_indices
    mock_top_k_result.values = mock_values
    mock_top_k.return_value = mock_top_k_result
    
    # Call endpoint
    response = client.post(
        "/predict/mobilenet",
        files={"file": ("test.jpg", create_test_image(), "image/jpeg")}
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "mobilenet"
    assert "predictions" in data
    assert len(data["predictions"]) == 5
    assert "inference_time_ms" in data


@patch('src.main.loaded_models')
@patch('src.main.mlflow.start_run')
@patch('src.main.mlflow.log_param')
@patch('src.main.mlflow.log_metric')
@patch('src.main.mlflow.set_tag')
@patch('src.main.tf.nn.softmax')
@patch('src.main.tf.nn.top_k')
def test_predict_non_rgb_image(mock_top_k, mock_softmax, mock_set_tag, mock_log_metric,
                                mock_log_param, mock_start_run, mock_models, client):
    """Test prediction converts non-RGB images correctly"""
    
    # MLflow context manager
    mock_start_run.return_value.__enter__.return_value = None
    mock_start_run.return_value.__exit__.return_value = None
    
    # Model is loaded
    mock_models.__contains__ = MagicMock(return_value=True)
    mock_model = MagicMock()
    fake_logits = tf.constant([[0.5, 0.3, 0.2, 0.1, 0.05]], dtype=tf.float32)
    mock_model.return_value = fake_logits
    mock_models.__getitem__ = MagicMock(return_value=mock_model)
    
    # Mock TensorFlow operations
    mock_softmax.return_value = fake_logits
    mock_top_k_result = MagicMock()
    mock_indices = MagicMock()
    mock_indices.__getitem__ = MagicMock(return_value=[
        MagicMock(numpy=MagicMock(return_value=i)) for i in range(5)
    ])
    mock_values = MagicMock()
    mock_values.__getitem__ = MagicMock(return_value=[
        MagicMock(numpy=MagicMock(return_value=v)) for v in [0.5, 0.3, 0.2, 0.1, 0.05]
    ])
    mock_top_k_result.indices = mock_indices
    mock_top_k_result.values = mock_values
    mock_top_k.return_value = mock_top_k_result
    
    # Create grayscale image
    img = Image.new('L', (224, 224), color=128)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    response = client.post(
        "/predict/mobilenet",
        files={"file": ("test.png", img_bytes, "image/png")}
    )
    
    assert response.status_code == 200


@patch("src.main.mlflow.tracking.MlflowClient")
def test_mlflow_health_connected(mock_mlflow_client, client):
    """Test MLflow health check when connected"""
    mock_client_instance = MagicMock()
    mock_client_instance.search_experiments.return_value = ["exp1", "exp2"]
    mock_mlflow_client.return_value = mock_client_instance

    response = client.get("/mlflow/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert "tracking_uri" in data
    assert data["experiments_count"] == 2


@patch("src.main.mlflow.tracking.MlflowClient")
def test_mlflow_health_disconnected(mock_mlflow_client, client):
    """Test MLflow health check when disconnected"""
    mock_mlflow_client.side_effect = Exception("MLflow unavailable")

    response = client.get("/mlflow/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "disconnected"
    assert "error" in data