import subprocess
import time
import requests


def start_container():
    # Build and start container using helper script
    subprocess.run(["./run-docker.sh", "run"], check=True)


def stop_container():
    subprocess.run(["./run-docker.sh", "stop"], check=False)


def wait_for_health(url: str, timeout: int = 60):
    """Wait until /health returns a JSON with model_loaded True or timeout."""
    deadline = time.time() + timeout
    last_exc = None
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                j = r.json()
                # Expect a dict with model_loaded and n_features
                if j.get("model_loaded") and isinstance(j.get("n_features"), int) and j.get("n_features") > 0:
                    return j
            last_exc = (r.status_code, r.text)
        except Exception as e:
            last_exc = e
        time.sleep(1)
    raise RuntimeError(f"Health check did not pass within {timeout}s, last: {last_exc}")


def test_service_health_and_model():
    base_url = "http://127.0.0.1:8000"
    health_url = f"{base_url}/health"

    try:
        start_container()
        j = wait_for_health(health_url, timeout=60)
        assert j.get("status") == "ok"
        assert j.get("model_loaded") is True
        assert isinstance(j.get("n_features"), int) and j.get("n_features") > 0
    finally:
        stop_container()
