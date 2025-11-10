from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.response import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import tensorflow as tf
import tensforflow_hub as hub
import numpy as np
from PIL import Image
import io
import logging

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

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
        "type" : "image_classification"
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
    # version = Optional[str]
    # accuracy = Optional[float]

class PredictionResponse(BaseModel):
    model : str
    predictions : List[Dict[str, Any]]
    inference_time_ms : float

@app.on_event("startup")
async def load_model():
    """Load Models on Startup"""
    logger.info("Loading Models Now...")
    try:
        for model_name, model_config in MODELS.items():
            logger.info(f"Loading {model_name}...")
            loaded_models[model_name] = hub.load(model_config["url"])
            logger.info(f"✓ {model_name} loaded successfully")
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