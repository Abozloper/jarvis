from pathlib import Path
import json
import sys

root = Path(sys.argv[1])

def replace(file, old, new):
    path = root / file
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"Unexpected upstream layout in {file}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")

replace("backend.js", "    delete env.JERVIS_ATTACH_PORT;", """
    if (this.app.isPackaged && process.platform === 'win32') {
      env.JARVIS_MASTER_DIR = path.join(process.resourcesPath, 'offline');
      env.OLLAMA_MODEL = 'qwen2.5:1.5b';
      env.JERVIS_STT_MODEL = 'base.en';
    }
    delete env.JERVIS_ATTACH_PORT;""".lstrip("\n"))
replace("local_ai.py", '        configured = os.getenv("OLLAMA_URL", "").rstrip("/")', '''
        bundled = os.getenv("JARVIS_MASTER_DIR")
        if bundled:
            binary = os.path.join(bundled, "ollama", "ollama.exe")
            model_dir = os.path.join(bundled, "models")
            if not os.path.isfile(binary) or not os.path.isdir(model_dir):
                raise SetupError("The bundled Ollama files are missing.", "Reinstall Jarvis from the master installer.")
            self._start_serve(binary, models_dir=model_dir)
            self._step("engine", "done", "Bundled Ollama is running.")
            return
        configured = os.getenv("OLLAMA_URL", "").rstrip("/")'''.lstrip("\n"))
replace("local_ai.py", "        self.use_vision = wants_vision()", '        self.use_vision = not os.getenv("JARVIS_MASTER_DIR") and wants_vision()')
replace("local_ai.py", "        self._check_disk(int(sum(APPROX_MODEL_BYTES", '''
        if os.getenv("JARVIS_MASTER_DIR"):
            raise SetupError("The bundled text model is missing.", "Reinstall Jarvis from the master installer.")
        self._check_disk(int(sum(APPROX_MODEL_BYTES'''.lstrip("\n"))
replace("stt_local.py", '    return os.path.join(paths.models_dir(), "whisper", MODEL)', '''
    bundled = os.getenv("JARVIS_MASTER_DIR")
    if bundled:
        return os.path.join(bundled, "speech")
    return os.path.join(paths.models_dir(), "whisper", MODEL)'''.lstrip("\n"))
replace("stt_local.py", "    from huggingface_hub import snapshot_download", '''
    if os.getenv("JARVIS_MASTER_DIR"):
        raise RuntimeError("The bundled speech model is missing. Reinstall Jarvis.")
    from huggingface_hub import snapshot_download'''.lstrip("\n"))
replace("selftest.py", "            stt_local.transcribe(clip.getvalue())", '''
            fixture = os.getenv("JARVIS_TEST_SPEECH_WAV")
            if fixture:
                with open(fixture, "rb") as sample:
                    spoken = stt_local.transcribe(sample.read())
                if "blue sky" not in spoken.casefold():
                    raise RuntimeError(f"Speech fixture was not recognized: {spoken!r}")
            else:
                stt_local.transcribe(clip.getvalue())'''.lstrip("\n"))
package = root / "package.json"
metadata = json.loads(package.read_text(encoding="utf-8"))
metadata["version"] = "1.0.6"
metadata["build"]["extraResources"].append({"from": "offline", "to": "offline", "filter": ["**/*"]})
package.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
