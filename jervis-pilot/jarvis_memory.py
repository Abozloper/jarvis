"""Local Hindsight service with durable background ingestion."""
import atexit
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import threading
import time
import requests

BASE = "http://127.0.0.1:8899"
BANK = BASE + "/v1/default/banks/jarvis/memories"
_lock = threading.Lock()
_worker = None
_process = None
_root = None
_status = "Memory is starting."
_session = requests.Session()
_session.trust_env = False

def connect():
    connection = sqlite3.connect(_root / "research.sqlite3", timeout=10)
    connection.execute("CREATE TABLE IF NOT EXISTS research (id TEXT PRIMARY KEY, content TEXT NOT NULL, created TEXT NOT NULL, synced INTEGER NOT NULL DEFAULT 0)")
    return connection

def stop():
    if _process and _process.poll() is None:
        _process.terminate()

atexit.register(stop)

def start(root, ollama_url):
    global _worker, _root
    with _lock:
        if _worker:
            return
        _root = Path(root) / "Memory"
        _root.mkdir(parents=True, exist_ok=True)
        with connect():
            pass
        _worker = threading.Thread(target=run, args=(ollama_url,), daemon=True)
        _worker.start()

def run(ollama_url):
    global _process, _status
    try:
        runtime = Path(os.environ["JARVIS_MASTER_DIR"]) / "hindsight"
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
                   HINDSIGHT_API_LLM_PROVIDER="ollama",
                   HINDSIGHT_API_LLM_BASE_URL=ollama_url,
                   HINDSIGHT_API_LLM_MODEL="qwen2.5:1.5b",
                   HINDSIGHT_API_EMBEDDINGS_PROVIDER="onnx",
                   HINDSIGHT_API_RERANKER_PROVIDER="flashrank",
                   HINDSIGHT_API_LLM_MAX_CONCURRENT="1",
                   HINDSIGHT_API_WORKER_ID="jarvis-desktop")
        _status = "Hindsight is starting. First use downloads its local memory models and database binaries."
        with (_root / "hindsight.log").open("a", encoding="utf-8") as log:
            _process = subprocess.Popen([str(runtime / "python.exe"), "-X", "utf8", "-m", "hindsight_api.main",
                                         "--host", "127.0.0.1", "--port", "8899"],
                                        env=env, cwd=str(_root), stdout=log, stderr=log,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for _ in range(600):
            if _process.poll() is not None:
                raise RuntimeError("Hindsight exited. See Memory/hindsight.log.")
            try:
                if _session.get(BASE + "/health", timeout=2).ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(2)
        else:
            raise RuntimeError("Hindsight startup timed out. Restart Jarvis to retry.")
        while _process.poll() is None:
            with connect() as db:
                row = db.execute("SELECT id, content, created FROM research WHERE synced=0 ORDER BY created LIMIT 1").fetchone()
            if not row:
                _status = "Hindsight is ready."
                time.sleep(3)
                continue
            _status = "Hindsight is indexing saved research in the background."
            try:
                response = _session.post(BANK, json={"items":[{"content":row[1], "document_id":row[0],
                    "timestamp":row[2], "metadata":{"saved_at":row[2]}}]}, timeout=(3,180))
                response.raise_for_status()
                if response.json().get("success") is not True:
                    raise ValueError("Memory ingestion was not confirmed")
                with connect() as db:
                    db.execute("UPDATE research SET synced=1 WHERE id=?", (row[0],))
            except (requests.RequestException, ValueError):
                _status = "Research is saved locally. Hindsight indexing will retry."
                time.sleep(30)
        raise RuntimeError("Hindsight stopped. Restart Jarvis to retry.")
    except Exception as error:
        _status = str(error)

def retain(question, answer):
    if _root is None:
        return
    now = datetime.now(timezone.utc).isoformat()
    content = "Research retrieved at " + now + "\nQuestion: " + question + "\n" + answer
    key = hashlib.sha256((question + "\n" + answer).encode()).hexdigest()
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO research(id,content,created) VALUES(?,?,?)", (key,content,now))

def recall(query):
    if _root is None:
        return ""
    try:
        response = _session.post(BANK + "/recall", json={"query":query,"max_tokens":700}, timeout=(1,3))
        response.raise_for_status()
        facts = response.json().get("results", [])
        return "\n".join(str(item.get("text","")) for item in facts[:5])
    except (requests.RequestException, ValueError):
        return ""

def command(text):
    clean = text.strip().rstrip(".!?").casefold()
    if clean in {"memory status", "hindsight status"}:
        return _status
    for prefix in ("search my memory for ", "recall research about ", "what do you remember about "):
        if clean.startswith(prefix):
            query = text[len(prefix):]
            facts = recall(query)
            if facts:
                return "Previously saved information; dates and details may have changed.\n" + facts
            return "No indexed memory was retrieved. " + _status
    return None
