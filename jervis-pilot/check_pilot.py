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

from datetime import date
import jarvis_research

class CalendarResponse:
    status_code = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def iter_content(self, *args, **kwargs):
        yield (b"<h4>What's Coming to Netflix on December 1st</h4><ul>"
               b"<li><strong>Example Film</strong> (2026) Original</li>"
               b"<li>A Series (Season 1)</li><li>Game (2026) Live event!</li></ul>")

def get_calendar(url, **kwargs):
    assert url.endswith("whats-coming-to-netflix-in-december-2026/")
    return CalendarResponse()

result = jarvis_research.answer("I want the top next 10 movies coming out in Netflix next month",
                                date(2026, 11, 12), get_calendar)
assert "1. Example Film" in result and "A Series" not in result and "Game" not in result
assert "release order" in result and "Source:" in result
assert jarvis_research.answer("Open Netflix") is None
assert "US catalog only" in jarvis_research.answer("Movies coming to Netflix next month in Colombia")

import jarvis_sources

with TemporaryDirectory() as folder:
    root = Path(folder)
    data = root / "Data"
    data.mkdir()
    (data / "pipeline.csv").write_text("Company,Status\nGems,Open\nAcme,Won\n", encoding="utf-8")
    def no_web(*args, **kwargs):
        raise AssertionError("Local data must stay local")
    assert "2 records" in jarvis_sources.answer("Summarize my sales pipeline", root, fake_chat, no_web)
    assert "Gems,Open" in jarvis_sources.answer("Search local datasets for Gems", root, fake_chat, no_web)
    assert jarvis_sources.answer("Look up Fleetwood Mac on Spotify", root, fake_chat, no_web) is None
    assert jarvis_sources.answer("Look up my notes about Gems", root, fake_chat, no_web) is None
    class WebResponse(CalendarResponse):
        def raise_for_status(self):
            pass
        class raw:
            @staticmethod
            def read(*args, **kwargs):
                return (b'<a class="result__a" href="https://example.org">Example</a>'
                        b'<a class="result__snippet">Verified example excerpt</a>')
    def get_web(url, **kwargs):
        assert kwargs["params"]["q"] == "example topic"
        return WebResponse()
    result = jarvis_sources.answer("Search the web for example topic", root, fake_chat, get_web)
    assert "Verified example excerpt" in result and "https://example.org" in result

import json
from jarvis_operations import Operations
with TemporaryDirectory() as folder:
    root = Path(folder)
    (root / "Data").mkdir()
    (root / "Data" / "jobs.json").write_text(json.dumps([
        {"id":"J-17","title":"Install","status":"delayed","due":"2026-11-12",
         "blocker":"Missing part","evidence":"Vendor confirmed a backorder","owner":"Sam"},
        {"id":"J-18","title":"Delivery","status":"open","due":"2026-11-12"},
        {"id":"J-19","title":"Repair","status":"open","due":"2026-11-12"},
        {"id":"J-20","title":"Quote","status":"open","due":"2026-11-12"},
    ]), encoding="utf-8")
    ops = Operations()
    brief = ops.answer("Jarvis, brief me on today’s operations and show the three items that need my attention.", root, date(2026,11,12))
    assert brief.count("[Data/jobs.json") == 3 and "J-17" in brief
    assert "Vendor confirmed a backorder" in ops.answer("Open the delayed job. What is holding it up?", root)
    preview = ops.answer("Draft the customer update and an internal follow-up task.", root)
    assert "CUSTOMER UPDATE" in preview and "INTERNAL FOLLOW-UP" in preview
    assert not (root / "Approved").exists()
    assert "no pending drafts" in ops.answer("Approve drafts for job J-18", root)
    assert not (root / "Approved").exists()
    assert "Saved both" in ops.answer("Approve drafts for job J-17", root)
    assert "Vendor confirmed a backorder" in (root / "Approved" / "J-17-drafts.txt").read_text(encoding="utf-8")

with TemporaryDirectory() as folder:
    root = Path(folder)
    (root / "Data").mkdir()
    (root / "Data" / "jobs.json").write_text(json.dumps([
        {"id":"J-1","title":"Private customer installation","status":"delayed",
         "blocker":"Check supplier availability","public_query":"example topic"}
    ]), encoding="utf-8")
    ops = Operations()
    for command in ["Brief me on today's operations", "Open the delayed job",
                    "Draft the customer update and an internal follow-up task"]:
        answer = ops.answer(command, root, chat=fake_chat, get=get_web)
        assert "https://example.org" in answer
    assert not (root / "Approved").exists()
    assert "Saved both" in ops.answer("Approve drafts for job J-1", root)
    assert "https://example.org" in (root / "Approved" / "J-1-drafts.txt").read_text(encoding="utf-8")
    def offline(*args, **kwargs):
        raise OSError("offline")
    assert "couldn't reach web search" in ops.answer("Open the delayed job", root, get=offline)
print("Operations web integration tests passed")

with TemporaryDirectory() as folder:
    root = Path(folder)
    (root / "Data").mkdir()
    (root / "Data" / "jobs.txt").write_text("Cobalt pump awaiting delivery\nBluefin valve approved", encoding="utf-8")
    assert "Cobalt pump" in jarvis_sources.answer("Jarvis, search local files for cobalt", root, fake_chat, no_web)
    assert "Bluefin valve" in jarvis_sources.answer("What about Bluefin?", root, fake_chat, no_web)
    assert "What topic" in jarvis_sources.local_search("what is the", root / "Data")
    jarvis_sources.answer("Open Spotify", root, fake_chat, no_web)
    assert jarvis_sources.answer("What about Bluefin?", root, fake_chat, no_web) is None

import jarvis_memory
with TemporaryDirectory() as folder:
    jarvis_memory._root = Path(folder)
    jarvis_memory.retain("Cobalt valve delivery", "Bluefin ships November 20. Source https://example.org/valve")
    result = jarvis_memory.archive_search("What did we find about the cobalt valve?")
    assert "Bluefin" in result and "https://example.org/valve" in result
    assert jarvis_memory.archive_search("what about the") == ""
    jarvis_memory._root = None
print("Conversational retrieval regression checks passed")
