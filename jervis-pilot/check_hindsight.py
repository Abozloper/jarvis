"""Exercise Hindsight retention and recall against a real local model."""
import subprocess
import time
import requests
from hindsight_client import Hindsight

def start():
    process = subprocess.Popen(["hindsight-api", "--host", "127.0.0.1", "--port", "8899"])
    for _ in range(180):
        if process.poll() is not None:
            raise RuntimeError("Hindsight exited")
        try:
            if requests.get("http://127.0.0.1:8899/health", timeout=2).ok:
                return process
        except requests.RequestException:
            pass
        time.sleep(2)
    process.terminate()
    raise RuntimeError("Hindsight startup timeout")

process = start()
try:
    client = Hindsight(base_url="http://127.0.0.1:8899")
    result = client.retain(bank_id="jarvis-test", content="The test supplier Bluefin ships the cobalt valve on November 20, 2026.")
    print("RETAIN", result, flush=True)
    result = client.recall(bank_id="jarvis-test", query="When does Bluefin ship the cobalt valve?")
    print("RECALL", result, flush=True)
    assert "bluefin" in str(result).lower() and "20" in str(result)
finally:
    process.terminate()
    process.wait(timeout=30)
process = start()
try:
    result = Hindsight(base_url="http://127.0.0.1:8899").recall(bank_id="jarvis-test", query="When does Bluefin ship the cobalt valve?")
    print("RECALL AFTER RESTART", result, flush=True)
    assert "bluefin" in str(result).lower() and "20" in str(result)
finally:
    process.terminate()
    process.wait(timeout=30)
