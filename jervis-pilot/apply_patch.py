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
