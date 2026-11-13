"""Stage and exercise the offline Windows payload used by the master installer."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import time
import zipfile

import requests
from huggingface_hub import snapshot_download

VERSION = "v0.34.4"
ENGINE = "ollama-windows-amd64.zip"
SHA256 = "535193f38f3344e5b08f5d1c171c31ce11aa17f0124ff69ae26d8ec7fe06fa62"
MODEL = "qwen2.5:1.5b"
URL = "http://127.0.0.1:11535"


def stage(root):
    root.mkdir(parents=True, exist_ok=True)
    runtime = root / "hindsight"
    runtime.mkdir(exist_ok=True)
    response = requests.get("https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip", timeout=120)
    response.raise_for_status()
    import io
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(runtime)
    (runtime / "python312._pth").write_text("python312.zip\n.\nsite-packages\nimport site\n", encoding="utf-8")
    subprocess.run([sys.executable, "-m", "pip", "install", "--target", str(runtime / "site-packages"),
                    "hindsight-api-slim[local-onnx,embedded-db]==1.2.1", "flashrank", "hindsight-client"],
                   check=True, timeout=900)
    subprocess.run([str(runtime / "python.exe"), "-c", "import hindsight_api, pg0, hindsight_client"],
                   check=True, timeout=60)
    with tempfile.TemporaryDirectory() as temp:
        archive = Path(temp) / ENGINE
        digest = hashlib.sha256()
        with requests.get(f"https://github.com/ollama/ollama/releases/download/{VERSION}/{ENGINE}",
                          stream=True, timeout=(30, 120)) as response, archive.open("wb") as output:
            response.raise_for_status()
            for chunk in response.iter_content(4 * 1024 * 1024):
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != SHA256:
            raise RuntimeError("Ollama archive checksum mismatch")
        with zipfile.ZipFile(archive) as files:
            for member in files.infolist():
                parts = PurePosixPath(member.filename).parts
                if any(part.casefold().startswith(("cuda", "cublas", "cudart", "rocm", "hipblas",
                                                    "amdhip", "rocblas", "vulkan")) for part in parts):
                    continue
                files.extract(member, root / "ollama")
    binary = root / "ollama" / "ollama.exe"
    if not binary.is_file():
        raise RuntimeError("The standalone archive did not contain ollama.exe at its root")
    snapshot_download(repo_id="Systran/faster-whisper-base.en", local_dir=root / "speech",
                      allow_patterns=["config.json", "model.bin", "tokenizer.json", "vocabulary.*",
                                      "preprocessor_config.json"])
    import shutil
    shutil.rmtree(root / "speech" / ".cache", ignore_errors=True)
    env = dict(os.environ, OLLAMA_HOST="127.0.0.1:11535", OLLAMA_MODELS=str(root / "models"),
               OLLAMA_LLM_LIBRARY="cpu", OLLAMA_NO_CLOUD="1")
    with (root.parent / "ollama-build.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen([str(binary), "serve"], env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(90):
                if server.poll() is not None:
                    raise RuntimeError("Bundled CPU Ollama exited during startup")
                try:
                    if requests.get(URL + "/api/version", timeout=2).ok:
                        break
                except requests.RequestException:
                    pass
                time.sleep(1)
            else:
                raise RuntimeError("Bundled CPU Ollama did not start")
            subprocess.run([str(binary), "pull", MODEL], env=env, check=True, timeout=900)
            show = requests.post(URL + "/api/show", json={"model": MODEL}, timeout=30)
            show.raise_for_status()
            model_license = show.json().get("license")
            if not model_license:
                raise RuntimeError("Missing text-model license")
            (root / "Qwen-LICENSE.txt").write_text(model_license, encoding="utf-8")
            answer = requests.post(URL + "/api/chat", json={
                "model": MODEL, "stream": False, "options": {"num_gpu": 0, "num_ctx": 4096, "num_predict": 32},
                "messages": [{"role": "user", "content": "What color is the sky on a clear day? Answer in one sentence."}],
            }, timeout=180)
            answer.raise_for_status()
            if "blue" not in answer.json()["message"]["content"].casefold():
                raise RuntimeError("CPU model failed the inference check")
            import jarvis_memory
            os.environ["JARVIS_MASTER_DIR"] = str(root)
            jarvis_memory.start(root.parent / "memory-smoke", URL)
            jarvis_memory.retain("When is the valve shipping?",
                                 "Bluefin ships the cobalt valve November 20, 2026. Source https://example.org/valve")
            for _ in range(240):
                with jarvis_memory.connect() as db:
                    synced = db.execute("SELECT COUNT(*) FROM research WHERE synced=1").fetchone()[0]
                if synced:
                    break
                if jarvis_memory._process and jarvis_memory._process.poll() is not None:
                    raise RuntimeError((jarvis_memory._root / "hindsight.log").read_text(encoding="utf-8", errors="replace")[-15000:])
                time.sleep(2)
            else:
                raise RuntimeError("Bundled Hindsight did not retain research")
            verified = requests.post(jarvis_memory.BANK + "/recall", json={"query":"Bluefin cobalt valve"}, timeout=30)
            verified.raise_for_status()
            if not verified.json().get("results"):
                raise RuntimeError("Hindsight returned no indexed facts")
            recalled = jarvis_memory.recall("When does Bluefin ship the cobalt valve?")
            if "bluefin" not in recalled.casefold():
                raise RuntimeError("Bundled Hindsight failed recall")
            print("Bundled Hindsight background research retention and recall passed")
            jarvis_memory.stop()
            os.environ.pop("JARVIS_MASTER_DIR", None)
        finally:
            server.terminate()
            server.wait(timeout=20)
    print("Bundled CPU Ollama and local text inference passed")


if __name__ == "__main__":
    stage(Path(sys.argv[1]).resolve())
