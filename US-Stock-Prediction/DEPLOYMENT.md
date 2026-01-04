# Deploying the US-Stock-Prediction Service to Cloud

This document provides clear, copyable commands and small code snippets to deploy the containerized `predict.py` service to Azure, AWS, and GCP. It assumes you already have the Docker image `us-stocks-predictor:latest` (or will build it during the flow) and that you want to deploy the container image to a managed container service.

Prerequisites
- Docker installed locally
- Cloud CLI for provider you use (`az`, `aws`, `gcloud`) configured and authenticated
- Project / resource group prepared in the cloud provider

Common commands
- Build image locally:
```bash
cd US-Stock-Prediction
docker build -t us-stocks-predictor:latest .
```
- Verify image works locally (optional):
```bash
docker run -p 8000:8000 --rm us-stocks-predictor:latest
curl http://localhost:8000/docs
```

When to mount a model vs bake it in
- If you want to update the model without rebuilding the image, store it in cloud storage (S3/GCS/Azure Blob) and download at container startup, or mount it via volume where supported.
- This repo currently supports baking `xgboost_model.joblib` into the image by default.

--------------------------
**Azure — App Service (Web App for Containers)**

1) Create an Azure Container Registry (ACR) and push image

```bash
# variables
RESOURCE_GROUP="rg-usstocks"
ACR_NAME="usstockacr$RANDOM"
IMAGE_NAME="us-stocks-predictor:latest"

az group create -n "$RESOURCE_GROUP" -l eastus
az acr create -n "$ACR_NAME" -g "$RESOURCE_GROUP" --sku Standard
az acr login -n "$ACR_NAME"

docker tag "$IMAGE_NAME" "$ACR_NAME.azurecr.io/$IMAGE_NAME"
docker push "$ACR_NAME.azurecr.io/$IMAGE_NAME"
```

2) Create an App Service and point to the container

```bash
APP_NAME="us-stocks-app-$RANDOM"
az appservice plan create -g "$RESOURCE_GROUP" -n "asp-$APP_NAME" --is-linux --sku B1
az webapp create -g "$RESOURCE_GROUP" -p "asp-$APP_NAME" -n "$APP_NAME" --deployment-container-image-name "$ACR_NAME.azurecr.io/$IMAGE_NAME"

# If ACR is private, grant pull permission
az webapp config container set -g "$RESOURCE_GROUP" -n "$APP_NAME" --docker-registry-server-url "https://$ACR_NAME.azurecr.io"
az webapp config appsettings set -g "$RESOURCE_GROUP" -n "$APP_NAME" --settings WEBSITES_PORT=8000
```

3) (Optional) If you need a storage blob for model updates

```bash
az storage account create -n usstockstorage$RANDOM -g "$RESOURCE_GROUP" -l eastus --sku Standard_LRS
# Use Azure Blob SDK inside container to download model at startup
```

Notes
- App Service will run the container and expose the mapped port. Set `WEBSITES_PORT=8000` as above.
- Alternatively, use Azure Container Instances (ACI) for a simpler container run, or AKS for Kubernetes.

--------------------------
**AWS — Amazon ECR + ECS (Fargate)**

1) Create ECR repo and push image

```bash
REGION=us-east-1
REPO_NAME=us-stocks-predictor
aws ecr create-repository --repository-name "$REPO_NAME" --region $REGION || true
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME"

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
docker tag us-stocks-predictor:latest "$ECR_URI:latest"
docker push "$ECR_URI:latest"
```

2) Deploy to ECS Fargate (quick using `ecs-cli` / CloudFormation or the console). Example using `aws ecs run-task` with an existing cluster is below; production should use a service behind a load balancer.

Example Fargate task definition (task-def.json):
```json
{
  "family": "us-stocks-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "us-stocks-container",
      "image": "REPLACE_WITH_ECR_URI:latest",
      "portMappings": [{"containerPort": 8000,"protocol": "tcp"}],
      "essential": true,
      "environment": [{"name":"ENV_VAR","value":"value"}]
    }
  ]
}
```

Register and run the task
```bash
aws ecs register-task-definition --cli-input-json file://task-def.json
# Create a cluster if not exists
aws ecs create-cluster --cluster-name us-stocks-cluster || true
# Run as a service behind ALB in production; quick run-task for testing:
aws ecs run-task --cluster us-stocks-cluster --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[subnet-...],assignPublicIp=ENABLED,securityGroups=[sg-...]}" --task-definition us-stocks-task
```

Notes
- For production use create an ECS Service with an Application Load Balancer (ALB).
- Use IAM roles for task execution and secrets via AWS Secrets Manager.

--------------------------
**GCP — Artifact Registry (or Container Registry) + Cloud Run**

1) Enable APIs and configure gcloud

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
PROJECT=$(gcloud config get-value project)
REGION=us-central1

# Create an Artifact Registry repo (Docker format)
gcloud artifacts repositories create us-stocks-repo --repository-format=docker --location=$REGION || true
```

2) Authenticate Docker and push

```bash
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet
IMAGE_NAME=$REGION-docker.pkg.dev/$PROJECT/us-stocks-repo/us-stocks-predictor:latest
docker tag us-stocks-predictor:latest "$IMAGE_NAME"
docker push "$IMAGE_NAME"
```

3) Deploy to Cloud Run

```bash
gcloud run deploy us-stocks-service --image "$IMAGE_NAME" --region $REGION --platform managed --allow-unauthenticated --port 8000
```

Notes
- Cloud Run automatically provisions HTTPS and scales to zero. Use `--memory` and `--concurrency` flags to tune.
- To protect the service, remove `--allow-unauthenticated` and configure IAM.

--------------------------
Secrets & models management (recommended patterns)
- Avoid baking credentials into the image. Use provider secret solutions:
  - Azure Key Vault + Managed Identity
  - AWS Secrets Manager / Parameter Store + IAM task role
  - GCP Secret Manager + Workload Identity
- If you want dynamic models consider storing model file in cloud storage (S3/GCS/Azure Blob) and have the container download it at startup. Example (pseudo):
```python
import os
from urllib.parse import urlparse
MODEL_URL = os.environ.get('MODEL_URL')
# download from S3/GCS/Azure Blob in startup code if MODEL_URL provided
```

--------------------------
CI/CD examples (GitHub Actions)

1) Deploy to GCP Cloud Run (workflow snippet)
```yaml
name: deploy-cloud-run
on: [push]
jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/setup-gcloud@v1
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: ${{ secrets.GCP_PROJECT }}
      - run: |
          docker build -t $REGION-docker.pkg.dev/${{ secrets.GCP_PROJECT }}/us-stocks-repo/us-stocks-predictor:latest .
          docker push $REGION-docker.pkg.dev/${{ secrets.GCP_PROJECT }}/us-stocks-repo/us-stocks-predictor:latest
      - run: |
          gcloud run deploy us-stocks-service --image $REGION-docker.pkg.dev/${{ secrets.GCP_PROJECT }}/us-stocks-repo/us-stocks-predictor:latest --region $REGION --platform managed --allow-unauthenticated
```

2) Deploy to AWS (push to ECR and update ECS service) — high-level steps:
- Set up `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in GitHub Secrets
- Build, login to ECR, push image
- Use `aws ecs update-service` to point running service to new task definition revision

--------------------------
Health check and testing
- Validate the service after deployment:
```bash
# Example: test /predict (use real JSON matching features)
curl -X POST https://<your-service-url>/predict -H "Content-Type: application/json" -d '{"revenue": 0, "revenue_growth": 0, ... }'
```

--------------------------
Troubleshooting tips
- Container exits immediately: check `docker logs` (or cloud provider logs) for stack trace. Common causes: missing model file, import failures, missing environment variables.
- Port configuration: ensure the cloud service routes to container port 8000 (many platforms default to 8080). Set app/platform port appropriately.
- Dependencies failing to install: confirm correct `requirements.txt` and system libs (xgboost may require `libgomp1` on some images).

If you want, I can also:
- Add a small startup script to support downloading the model from cloud storage at boot.
- Create provider-specific full Terraform or CloudFormation manifests for infra-as-code.

---
Saved as `DEPLOYMENT.md` in this folder. Follow the provider section you prefer and adapt resource names to your account.
