from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
from jarvis_pilot import handle
import subprocess
import sys

def fake_chat(**kwargs):
    assert "Northstar" in kwargs["messages"][1]["content"]
    return NS(choices=[NS(message=NS(content="Northstar draft"))])

with TemporaryDirectory() as folder:
    root = Path(folder)
    def command(text, url="http://127.0.0.1:11434"):
        return handle(text, root, fake_chat, url)
    assert command("Open Outlook") is None
    assert command("daily brief") == "You have no saved notes yet."
    assert command("Remember that I promised to call Dan Friday.") == "Saved: I promised to call Dan Friday."
    code = 'from jarvis_pilot import handle; import sys; print(handle("daily brief", sys.argv[1], None, ""))'
    assert "call Dan Friday" in subprocess.check_output([sys.executable, "-c", code, folder], text=True)
    assert "requires" in command("draft lead follow-ups", "https://example.com")
    assert "I saved" in command("draft lead follow-ups")
    assert (root / "lead-drafts.txt").read_text(encoding="utf-8") == "Northstar draft\n"
    (root / "inbox.txt").write_text("x" * 4501, encoding="utf-8")
    assert "shorten" in command("draft lead follow-ups")
    assert (root / "lead-drafts.txt").read_text(encoding="utf-8") == "Northstar draft\n"
print("Pilot tests passed")

from jarvis_pilot import relevant_notes

with TemporaryDirectory() as folder:
    root = Path(folder)
    assert relevant_notes("What time does Gems open Saturday?", root) == []
    handle("Learn that Gems opens at 9 a.m. on Saturdays.", root, fake_chat, "http://localhost")
    handle("Remember that the spare charger is in the blue drawer.", root, fake_chat, "http://localhost")
    assert relevant_notes("What time does Gems open Saturday?", root) == [
        "Gems opens at 9 a.m. on Saturdays."
    ]
    assert relevant_notes("Where is the spare charger?", root) == [
        "the spare charger is in the blue drawer."
    ]
    assert relevant_notes("Why is the sky blue?", root) == []
