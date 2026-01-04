# US-Stock-Prediction — Docker instructions

Quick instructions to build and run the FastAPI app packaged in this folder.

Prerequisites
- Docker installed and available on your machine.
- (Optional) `xgboost_model.joblib` model file in this folder, or mount it at runtime.

Build the image
```bash
cd US-Stock-Prediction
docker build -t us-stocks-predictor:latest .
```

Run (production — recommended)
- This command mounts the local `xgboost_model.joblib` into the container. If you included the model in the image, omit the `-v` mount.
```bash
docker run -d --name us-predict -p 8000:8000 -v $(pwd)/xgboost_model.joblib:/app/xgboost_model.joblib us-stocks-predictor:latest
```

Run (development with auto-reload)
```bash
docker run -d --name us-predict -p 8000:8000 -e UVICORN_RELOAD=1 -v $(pwd):/app us-stocks-predictor:latest
```

Stop and remove container
```bash
docker rm -f us-predict
```

Quick curl test
```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"<feature1>": 0, "<feature2>": 1, ... }'
```

Notes
- The `Dockerfile` sets `UVICORN_RELOAD=0` by default; set the env var `UVICORN_RELOAD=1` to enable `--reload`.
- `.dockerignore` currently excludes `xgboost_model.joblib`. If you want the model inside the image, remove that line and rebuild.
- If your environment requires pinned versions, adjust `requirements.txt` accordingly.

Helper script
- A `run-docker.sh` helper script is included for convenience. Make it executable before running:
```bash
chmod +x run-docker.sh
./run-docker.sh build
# US-Stock-Prediction

This repository packages a FastAPI service that serves predictions from an XGBoost model trained on U.S. stock financial indicators. The service exposes a `/predict` endpoint that accepts a JSON object of financial indicator features and returns a categorical prediction describing whether the stock value is expected to increase or decrease.

**Dataset and purpose**

- Dataset source: OpenML dataset id 46527 (search page: https://www.openml.org/search?type=data&status=active&id=46527&sort=runs). This dataset contains many financial indicators (hundreds of features) for U.S. stocks and is useful for building supervised models that predict stock movement labels.
- Problem: given a snapshot of financial indicators for a company, predict whether the stock value will increase or decrease.
- How the solution is used: the model is packaged into a container and served with FastAPI. Clients POST feature vectors to `/predict` and receive a high-level label `stock_value_increase` or `stock_value_decrease`.

**Project contents**

- `predict.py` — FastAPI app that dynamically builds a Pydantic input model from the dataset feature names, loads `xgboost_model.joblib` and exposes `/predict`.
- `train.py` — training script (keeps your model training code in one place; modify as needed to retrain and export `xgboost_model.joblib`).
- `test_case.py` — small script you can use to validate the model locally.
- `xgboost_model.joblib` — the exported trained model (this repository bakes it into the Docker image by default).
- `Dockerfile`, `run-docker.sh`, `requirements.txt` — containerization and run helpers.
- `DEPLOYMENT.md` — provider-specific instructions to deploy the container to Azure, AWS, and GCP.

How to use and implement locally

1) Install dependencies (recommended to use a virtualenv):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Run the FastAPI app locally (development):

```bash
uvicorn predict:app --reload --host 0.0.0.0 --port 8000
```

3) Browse the interactive API docs at `http://localhost:8000/docs` to see the expected input schema and test requests.

4) Run unit / smoke tests:

```bash
python test_case.py
```

How to use it with Docker

We provide a `Dockerfile` and `run-docker.sh` to make building and running the service straightforward.

Build the image

```bash
cd US-Stock-Prediction
docker build -t us-stocks-predictor:latest .
```

Run (production — image contains the model by default)

```bash
./run-docker.sh run
# or directly
docker run -d --name us-predict -p 8000:8000 us-stocks-predictor:latest
```

Run (development with live reload)

```bash
./run-docker.sh dev
```

Test the running service (example with curl):

```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"revenue": 0, "revenue_growth": 0, ... }'
```

Notes about the model file

- The image built by default includes `xgboost_model.joblib`. If you prefer to mount the model at runtime or download it from cloud storage, modify `run-docker.sh` or `predict.py` to fetch the model at startup.

Deployment to Cloud

For provider-specific deployment steps and copyable commands for Azure, AWS, and GCP, see `DEPLOYMENT.md` in this folder. That document walks through pushing the image to a registry (ACR / ECR / Artifact Registry) and deploying to the managed container services (App Service, ECS Fargate, Cloud Run).

Recommendations and next steps

- If you plan to update the model frequently, store it in cloud storage and add a small startup script that downloads it at container start. See `DEPLOYMENT.md` "Secrets & models management" for patterns.
- Add a `/health` endpoint for lightweight readiness checks used by container platforms and load balancers.
- Add CI/CD (GitHub Actions) to build, test, push, and deploy automatically (there is an example snippet in `DEPLOYMENT.md`).

If you want, I can:
- Add a health endpoint to `predict.py` and update tests.
- Add a startup script that downloads the model from S3/GCS/Azure Blob if a `MODEL_URL` environment variable is set.
- Provide a full GitHub Actions workflow that builds and deploys to your chosen provider.

---
Last updated: see repository history.
