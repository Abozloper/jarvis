from pathlib import Path
import sys

root = Path(sys.argv[1])
app = root / "app.py"
source = app.read_bytes()
newline = b"\r\n" if b"\r\n" in source else b"\n"
anchor = b"            direct_result = handle_direct_command(text)"
if source.count(anchor) != 1 or source.count(b"import local_llm" + newline) != 1:
    raise SystemExit("Unexpected upstream dispatch layout")
source = source.replace(b"import local_llm" + newline, b"import local_llm" + newline + b"import jarvis_pilot" + newline)
source = source.replace(anchor, newline.join([
    b'            pilot_reply = jarvis_pilot.handle(text, paths.data("Pilot"), local_llm.chat, local_llm.URL) if not isinstance(text, ImageCaption) else None',
    b'            direct_result = PrivateReply(pilot_reply) if pilot_reply else handle_direct_command(text)',
]))
app.write_bytes(source)

def update(name, changes):
    path = root / name
    with path.open(encoding="utf-8", newline="") as file:
        text = file.read()
    line_end = "\r\n" if "\r\n" in text else "\n"
    for old, new in changes:
        old, new = old.replace("\n", line_end), new.replace("\n", line_end)
        if old not in text:
            raise SystemExit(f"Expected text missing in {name}: {old!r}")
        text = text.replace(old, new)
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text)


update("index.html", [("Jervis", "Jarvis")])
update("main.js", [("title: 'Jervis'", "title: 'Jarvis'")])
update("renderer.js", [("Jervis", "Jarvis")])
update("app.py", [
    ('            if mic_muted.is_set():\n                send_status("muted")',
     '            if os.getenv(\'JERVIS_RECOVERY_AUDIO\') == \'1\' or mic_muted.is_set():\n                send_status("muted")'),
    ('        _devices["microphones"] = list_microphones()\n        _devices["voices"] = osal.list_voices()',
     '        _devices["microphones"] = [] if os.getenv('JERVIS_RECOVERY_AUDIO') == '1' else list_microphones()\n        _devices["voices"] = [] if os.getenv('JERVIS_RECOVERY_AUDIO') == '1' else osal.list_voices()'),
])
update("backend.js", [
    ("    this.crashes = [];\n    this.stopping = false;",
     "    this.crashes = [];\n    this.textOnly = process.argv.includes('--text-only');\n    this.stopping = false;"),
    ("      PYTHONUNBUFFERED: '1',", "      PYTHONFAULTHANDLER: '1',\n      PYTHONUNBUFFERED: '1',"),
    ("    delete env.JERVIS_ATTACH_PORT;",
     "    if (this.textOnly) { env.JERVIS_AUDIO = 'off'; env.JERVIS_RECOVERY_AUDIO = '1'; }\n    delete env.JERVIS_ATTACH_PORT;"),
    ("    forward(child.stderr);",
     "    if (!this.app.isPackaged) forward(child.stderr);\n"
     "    else child.stderr.on('data', (chunk) => this.log('Engine stderr: ' + chunk.toString('utf8').slice(0, 4000).trim()));"),
    ("    if (this.crashes.length >= MAX_CRASHES) {",
     "    if (this.crashes.length >= MAX_CRASHES) {\n"
     "      if (process.platform === 'win32' && !this.textOnly && process.env.JERVIS_AUDIO !== 'off') {\n"
     "        this.textOnly = true;\n"
     "        this.crashes = [];\n"
     "        const detail = 'Jarvis will retry with audio off. Use the text box if it starts.';\n"
     "        this.log(detail);\n"
     "        this.onState('restarting', detail);\n"
     "        this.spawn();\n"
     "        return;\n"
     "      }"),
    ("Jervis’s engine", "Jarvis’s engine"),
    ("Jervis's engine", "Jarvis's engine"),
])
