#!/usr/bin/env bash
set -euo pipefail

# Helper script to build/run/stop the Docker container for this project.
# Usage:
#   ./run-docker.sh build   # build the image
#   ./run-docker.sh run     # stop, build, and run (production mount model)
#   ./run-docker.sh dev     # stop, build, and run in dev (bind mount source, uvicorn --reload)
#   ./run-docker.sh stop    # stop and remove container

IMAGE="us-stocks-predictor:latest"
CONTAINER="us-predict"
MODEL_HOST_PATH="$(pwd)/xgboost_model.joblib"

build() {
  docker build -t "$IMAGE" .
}

stop() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}

run_prod() {
  stop
  build
  if [ -f "$MODEL_HOST_PATH" ]; then
    docker run -d --name "$CONTAINER" -p 8000:8000 -v "$MODEL_HOST_PATH":/app/xgboost_model.joblib "$IMAGE"
  else
    echo "Warning: $MODEL_HOST_PATH not found. Running without a model mount."
    docker run -d --name "$CONTAINER" -p 8000:8000 "$IMAGE"
  fi
}

run_dev() {
  stop
  build
  docker run -d --name "$CONTAINER" -p 8000:8000 -e UVICORN_RELOAD=1 -v "$(pwd)":/app "$IMAGE"
}

case "${1:-}" in
  build)
    build
    ;;
  run)
    run_prod
    ;;
  dev)
    run_dev
    ;;
  stop)
    stop
    ;;
  *)
    cat <<EOF
Usage: $0 {build|run|dev|stop}

Commands:
  build   Build the Docker image
  run     Stop, build, and run the container (mounts local model if present)
  dev     Stop, build, and run with source bind-mounted and uvicorn reload enabled
  stop    Stop and remove the container
EOF
    exit 1
    ;;
esac
