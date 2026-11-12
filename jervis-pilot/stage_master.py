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
                "model": MODEL, "stream": False, "options": {"num_gpu": 0, "num_predict": 32},
                "messages": [{"role": "user", "content": "What color is the sky on a clear day? Answer in one sentence."}],
            }, timeout=180)
            answer.raise_for_status()
            if "blue" not in answer.json()["message"]["content"].casefold():
                raise RuntimeError("CPU model failed the inference check")
        finally:
            server.terminate()
            server.wait(timeout=20)
    print("Bundled CPU Ollama and local text inference passed")


if __name__ == "__main__":
    stage(Path(sys.argv[1]).resolve())
