from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.response import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import tensorflow as tf
import tensorflow_hub as hub
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

@app.get("/models", response_model=List[ModelInfo])
async def list_models():
    """List of all available models"""
    models_info = []
    for name, config in MODELS.items():
        models_info.append(ModelInfo(
            name = name,
            description = config["description"],
            type = config["type"],
            status = "loaded" if name in loaded_models else "not_loaded"
        ))
    return models_info


@app.post("/predict/{model_name}", response_model = PredictionResponse)
async def predict(model_name:str, file: UploadFile = File(...)):
    """Make predictions using Specified Model"""
    import time
    if model_name not in MODELS:
        raise HTTPException(status_code = 404, detail = f"Model {model_name} not found")
    
    if model_name not in loaded_models:
        raise HTTPException(status_code = 503, detail = f"Model {model_name} not loaded")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        target_size = MODELS[model_name]["input_shape"][:2]
        image = image.resize(target_size)
        
        # Convert to array and normalize
        img_array = np.array(image) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        
        # Make prediction
        start_time = time.time()
        predictions = loaded_models[model_name](img_array)
        inference_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Get top 5 predictions
        top_k = tf.nn.top_k(predictions, k=5)

        results = []
        for i in range(5):
            results.append({
                "class_id": int(top_k.indices[0][i].numpy()),
                "confidence": float(top_k.values[0][i].numpy())
            })
        
        return PredictionResponse(
            model=model_name,
            predictions=results,
            inference_time_ms=round(inference_time, 2)
        )

    except Exception as e:
        logger.error(f"Prediction Error: {str(e)}")
        raise HTTPException(status_code = 500, detail = str(e))
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    