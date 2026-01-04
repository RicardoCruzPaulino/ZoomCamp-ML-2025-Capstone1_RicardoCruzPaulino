FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps needed by some Python packages (build tools and libgomp for xgboost)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc g++ libgomp1 git curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app files
COPY . /app

EXPOSE 8000

# Use a simple exec-form CMD for clean signal handling. For development
# (auto-reload) run the container with the `run-docker.sh dev` helper which
# bind-mounts sources and passes `UVICORN_RELOAD=1` and uses the host's uvicorn.
CMD ["uvicorn", "predict:app", "--host", "0.0.0.0", "--port", "8000"]
