# ML Deployment Platform

Production-grade ML model deployment platform with experiment tracking, containerization, and Kubernetes orchestration.

## Features
- **FastAPI** backend for model serving
- **MLflow** integration for experiment tracking and model versioning
<!-- - **Docker** multi-stage builds (86% size reduction)  -->
- **Kubernetes** deployment with service discovery
- Automated logging of predictions and metrics

---

## MLflow Integrated 🔬

Comprehensive experiment tracking for all model predictions.

### What Gets Logged

**Model Loading:**
- Model name, type, and version
- Model URL and input shape
- Loading timestamp

**Predictions:**
- Model used
- Image filename and dimensions
- Inference time (ms)
- Top 5 predictions with confidence scores
- Timestamp

### Accessing MLflow UI

**Docker Compose:**
```bash
docker-compose up
open http://localhost:5000
```

**Kubernetes:**
```bash
kubectl port-forward svc/mlflow-service 5000:5000
open http://localhost:5000
```

### Model Registry
```json
{
  "name": "mobilenet",
  "version": "1.0.0",
  "framework": "tensorflow",
  "framework_version": "2.14.0"
}
```

### Screenshots
![MLflow Dashboard](docs/Experiments_list.png)
![Experiment Details](docs/job_description.png)
![Metrics Tracking](docs/job_metrics.png)

---

## Kubernetes Deployment

### Architecture
- **2 FastAPI pods** - Load balanced via Service
- **1 MLflow pod** - Experiment tracking backend
- **Services:** 
  - `ml-api-service` (NodePort) - External access
  - `mlflow-service` (ClusterIP) - Internal communication
- **Service Discovery** - Pods communicate via K8s DNS

### Deploy to Minikube
```bash
# Start Minikube
minikube start

# Use Minikube's Docker daemon
eval $(minikube docker-env)

# Build image
docker build -t ml-deployment-platform-api:latest .

# Deploy all components
kubectl apply -f k8s/

# Get access URL
minikube service ml-api-service --url

# Test API
curl http://<url-from-above>/

# Test prediction
curl -X POST http://<url>/predict/mobilenet -F "file=@test_image.jpg"
```

### Verify Deployment
```bash
# Check pods
kubectl get pods

# Check services
kubectl get svc

# View logs
kubectl logs -l app=ml-api

# Access MLflow
kubectl port-forward svc/mlflow-service 5000:5000
```

### Future Enhancements
- [ ] Persistent Volumes for MLflow data
- [ ] Liveness/Readiness probes for self-healing
- [ ] Resource requests/limits
- [ ] Horizontal Pod Autoscaling
- [ ] Ingress controller for production routing

---

## Local Development (Docker Compose)
```bash
docker-compose up
open http://localhost:8000/docs
```