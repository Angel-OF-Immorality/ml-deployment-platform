from fastapi import FastAPI, File, UploadFile, HTTPException
# from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
from PIL import Image
import io
import logging
import mlflow
import mlflow.tensorflow
import os
from datetime import datetime
# from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

# Configure MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("ml-deployment-platform")

logger.info(f"MLflow tracking URI: {MLFLOW_TRACKING_URI}")

app = FastAPI(
    title = "ML Development Platform",
    description = "Automated ML model serving Platform",
    version = "1.0.0"
)

MODELS = {
    "mobilenet" : {
        "url" : "https://tfhub.dev/google/tf2-preview/mobilenet_v2/classification/4",
        "description" : "Mobile Net V2 for image classification",
        "input_shape" : (224,224,3),
        "type" : "image_classification",
        "version": "1.0.0",
        "framework": "tensorflow",
        "framework_version": "2.14.0"
    }
}

#Global Model Cache
#So that I don't have to load a model each time for predictions
loaded_models = {}

#Data modelling
#from typing import Optional
class ModelInfo(BaseModel):
    name : str
    description : str
    type : str
    status : str
    version : str
    framework : str
    # accuracy = Optional[float]

class PredictionResponse(BaseModel):
    model : str
    predictions : List[Dict[str, Any]]
    inference_time_ms : float

@app.on_event("startup")
async def load_models():
    """Load Models on Startup"""
    logger.info("Loading Models Now...")
    try:
        for model_name, model_config in MODELS.items():
            logger.info(f"Loading {model_name}...")

            with mlflow.start_run(run_name = f"load_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                loaded_models[model_name] = hub.load(model_config["url"])
                
                mlflow.log_param("model_name", model_name)
                mlflow.log_param("model_type", model_config["type"])
                mlflow.log_param("model_url", model_config["url"])
                mlflow.log_param("input_shape", str(model_config["input_shape"]))
                mlflow.set_tag("stage", "model_loading")
                mlflow.set_tag("version", "1.0.0")

                logger.info(f"✓ {model_name} loaded successfully")
                logger.info(f"✓ {model_name} metadata logged to MLflow")

    except Exception as e:
        logger.error(f"Error loading models: {str(e)}")


@app.get("/")
async def root():
    """Root Endpoint"""
    return {
        "service" : "ML deployment Platform",
        "version" : "1.0.0",
        "status" : "operational"
    }

# Prometheus metrics
# REQUEST_COUNT = Counter('ml_api_requests_v2_total', 'Total API requests', ['endpoint', 'method'])
# REQUEST_DURATION = Histogram('ml_api_request_duration_v2_seconds', 'Request duration', ['endpoint'])
# PREDICTION_COUNT = Counter('ml_predictions_v2_total', 'Total predictions', ['model'])

@app.get("/metrics")
async def metrics():
    return Response(
        generate_latest(),media_type=CONTENT_TYPE_LATEST
    )

@app.get("/health")
async def health_check():
    """Health Check Endpoint"""
    models_status = {
        name: "loaded" if name in loaded_models else "not_loaded" for name in MODELS.keys()
    }

    return {
        "status" : "healthy",
        "models" : models_status,
        "total_models" : len(MODELS)
    }

@app.get("/mlflow/health")
async def mlflow_health():
    "Check MLFLow Connection"
    try:
        client = mlflow.tracking.MlflowClient()
        experiments = client.search_experiments()
        return {
            "status" : "connected",
            "tracking_uri" : MLFLOW_TRACKING_URI,
            "experiments_count" : len(experiments)
        }
    except Exception as e:
        return {
            "status" : "disconnected",
            "error" : str(e)
        }

@app.get("/models", response_model=List[ModelInfo])
async def list_models():
    """List of all available models"""
    models_info = []
    for name, config in MODELS.items():
        models_info.append(ModelInfo(
            name = name,
            description = config["description"],
            type = config["type"],
            status = "loaded" if name in loaded_models else "not_loaded",
            version = config["version"],
            framework = config["framework"]
        ))
    return models_info


@app.post("/predict/{model_name}", response_model = PredictionResponse)
async def predict(model_name:str, file: UploadFile = File(...)):
    """Make predictions using Specified Model"""

    if model_name not in MODELS:
        raise HTTPException(status_code = 404, detail = f"Model {model_name} not found")
    
    if model_name not in loaded_models:
        raise HTTPException(status_code = 503, detail = f"Model {model_name} not loaded")
    
    with mlflow.start_run(run_name=f"predict_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        try:

            mlflow.log_param("model_name", model_name)
            mlflow.log_param("image_filename", file.filename)
            mlflow.set_tag("stage", "inference")

            contents = await file.read()
            image = Image.open(io.BytesIO(contents))

            mlflow.log_param("image_mode", image.mode)
            mlflow.log_param("image_size", f"{image.size[0]}x{image.size[1]}")

            if image.mode != 'RGB':
                image = image.convert('RGB')

            target_size = MODELS[model_name]["input_shape"][:2]
            image = image.resize(target_size)
            
            # Convert to array and normalize
            img_array = np.array(image, dtype=np.float32) / 255.0
            img_array = np.expand_dims(img_array, axis=0).astype(np.float32)
            
            # Make prediction
            start_time = time.time()
            predictions = loaded_models[model_name](img_array)
            predictions = tf.nn.softmax(predictions)
            inference_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # REQUEST_COUNT.labels(endpoint='predict_' + model_name, method='POST').inc()
            mlflow.log_metric("inference_time_ms", inference_time)
            
            # Get top 5 predictions
            top_k = tf.nn.top_k(predictions, k=5)

            results = []
            for i in range(5):
                class_id = int(top_k.indices[0][i].numpy())
                confidence = float(top_k.values[0][i].numpy())
                results.append({
                    "class_id" : class_id,
                    "confidence" : confidence
                })

            mlflow.log_metric("top_confidence", results[0]["confidence"])
            mlflow.log_param("top_class_id", results[0]["class_id"])
            
            #logging all predictions:
            for i, pred in enumerate(results):
                mlflow.log_metric(f"class_{i+1}_confidence", pred["confidence"])
                mlflow.log_param(f"class_{i+1}_id", pred["class_id"])
            logger.info(f"Prediction logged to MLFlow - Top Class: {results[0]['class_id']}, Confidence: {results[0]['confidence']:.4f}")

            # PREDICTION_COUNT.labels(model=model_name).inc()
            # REQUEST_DURATION.labels(endpoint='predict_' + model_name).observe(inference_time/1000)

            return PredictionResponse(
                model=model_name,
                predictions=results,
                inference_time_ms=round(inference_time, 2)
            )
        except Exception as e:
            mlflow.log_param("error", str(e))
            mlflow.set_tag("status", "failed")
            logger.error(f"Prediction Error: {str(e)}")
            raise HTTPException(status_code = 500, detail = str(e))
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    