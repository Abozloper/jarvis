"""Operations briefing and approval-gated drafts from local job records."""
import json
import hashlib
import re
from datetime import date
from pathlib import Path
import requests
from jarvis_sources import public_web


class Operations:
    def __init__(self):
        self.selected = None
        self.pending = None
        self.research = {}

    def external(self, job, chat, get):
        query = job.get("public_query", "").strip()
        if not query:
            return ""
        result = public_web(query, chat, get)
        self.research[job["id"].casefold()] = result
        return "\nPublic research (external context, relevance to this job requires verification):\n" + result

    def answer(self, text, root, today=None, chat=None, get=requests.get):
        text = " ".join(text.strip().rstrip(".!?").casefold().split())
        text = re.sub(r"^(?:hey )?(?:jarvis|jervis)[, ]+\s*", "", text)
        root = Path(root).resolve()
        if self.selected and self.selected[0] != root:
            self.selected = None
            self.pending = None
        aliases = {
            "what needs my attention": "operations brief",
            "what needs my attention today": "operations brief",
            "what are my priorities today": "operations brief",
            "how is the business doing today": "operations brief",
            "what's holding it up": "open the delayed job",
            "what is holding it up": "open the delayed job",
            "why is it delayed": "open the delayed job",
            "draft an update": "draft the customer update and an internal follow-up task",
            "draft a customer update": "draft the customer update and an internal follow-up task",
            "prepare the follow-up": "draft the customer update and an internal follow-up task",
        }
        contextual = text in {"what's holding it up", "what is holding it up", "why is it delayed"}
        text = aliases.get(text, text)
        if contextual and self.selected:
            text += " " + self.selected[1]
        text = re.sub(r"^(?:open|investigate|show me) (?:job|record) ([a-z0-9_-]+)$", r"open the delayed job \1", text)
        today = today or date.today()
        brief = re.match(r"^(?:brief me on (?:today['’]s )?operations|(?:give me )?(?:my |today['’]s )?operations brief)", text)
        investigate = re.match(r"^(?:open|investigate|show me) (?:the )?delayed job(?: ([a-z0-9_-]+))?(?=[ ,.]|$)", text)
        draft = re.fullmatch(r"(?:prepare|draft) (?:the |a )?customer update and (?:an |the )?internal follow[- ]up task", text)
        approve = re.fullmatch(r"approve (?:drafts|draft) for (?:job )?([a-z0-9_-]+)", text)
        if text == "cancel drafts":
            self.pending = None
            return "Draft preview cancelled."
        if approve:
            if not self.pending or self.pending[0].casefold() != approve[1] or self.pending[2] != root:
                return "There are no pending drafts for that job. Ask me to draft them first."
            job_id, preview, _, fingerprint = self.pending
            try:
                current = hashlib.sha256((root / "Data" / "jobs.json").read_bytes()).hexdigest()
            except OSError:
                return "I couldn't recheck the job records. Restore Data/jobs.json before approving."
            if current != fingerprint:
                self.pending = None
                return "The job records changed after this draft. Ask me to draft it again before approving."
            try:
                folder = root / "Approved"
                folder.mkdir(exist_ok=True)
                path = folder / f"{job_id}-drafts.txt"
                with path.open("x", encoding="utf-8") as file:
                    file.write(preview + "\n")
            except FileExistsError:
                if path.read_text(encoding="utf-8") != preview + "\n":
                    return f"An approved file already exists for {job_id}. Move it before approving this revision."
            except OSError:
                return "I couldn't save the approved drafts."
            self.pending = None
            return f"Saved both approved drafts locally to {path}."
        if not (brief or investigate or draft):
            return None
        try:
            with (root / "Data" / "jobs.json").open("rb") as file:
                snapshot = file.read(1_000_001)
            raw = snapshot.decode("utf-8-sig")
            rows = json.loads(raw) if len(raw) <= 1_000_000 else None
            if not isinstance(rows, list):
                raise ValueError
            jobs = {}
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError
                job = {key: row.get(key, "") for key in (
                    "id", "title", "status", "due", "blocker", "evidence", "owner", "next_step", "public_query")}
                if (any(not isinstance(value, str) for value in job.values())
                        or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", job["id"])
                        or not job["title"] or not job["status"] or job["id"].casefold() in jobs):
                    raise ValueError
                job["due"] = date.fromisoformat(job["due"]) if job["due"] else None
                jobs[job["id"].casefold()] = job
        except (OSError, ValueError, UnicodeError):
            return "I couldn't read Data/jobs.json. Add or correct the local job records before trying again."

        active = [job for job in jobs.values()
                  if job["status"].casefold() not in {"done", "closed", "complete", "completed", "cancelled", "canceled"}]
        urgent = [job for job in active if job["status"].casefold() in {"delayed", "blocked"}
                  or (job["due"] and job["due"] <= today)]
        urgent.sort(key=lambda job: (job["status"].casefold() not in {"blocked", "delayed"},
                                     job["due"] or date.max, job["id"]))
        if brief:
            lines = [f"Operations brief for {today}. {len(active)} active jobs, {len(urgent)} need attention."]
            for job in urgent[:3]:
                issue = job["blocker"] or (f"Due {job['due']}" if job["due"] else job["status"])
                lines.append(f"{job['id']} — {job['title']}: {issue}. [Data/jobs.json, {job['id']}]")
                lines.append(self.external(job, chat, get))
            return "\n".join(lines)
        if investigate:
            delayed = [job for job in urgent if job["status"].casefold() in {"blocked", "delayed"}]
            requested = investigate[1]
            if requested in {"what", "why", "and", "which"}:
                requested = None
            if requested:
                job = jobs.get(requested)
            else:
                if len(delayed) > 1:
                    return "Which delayed job? Say open the delayed job followed by its ID: " + ", ".join(j["id"] for j in delayed[:10])
                job = delayed[0] if delayed else None
            if not job:
                return "I couldn't find that job in Data/jobs.json."
            self.pending = None
            self.selected = (root, job["id"].casefold())
            return (f"{job['id']} — {job['title']} ({job['status']}).\n"
                    f"Blocker: {job['blocker'] or 'Not recorded'}.\n"
                    f"Supporting evidence: {job['evidence'] or 'No evidence recorded'}.\n"
                    f"Source: Data/jobs.json, record {job['id']}.") + self.external(job, chat, get)
        job = jobs.get(self.selected[1]) if self.selected and self.selected[0] == root else None
        if not job:
            return "Open the delayed job first so I know which customer update to draft."
        job_id = job["id"]
        customer = (f"Hello,\nI'm writing with an update on {job['title']} ({job_id}). "
                    f"The current status is {job['status']}. We're checking the schedule and will share a confirmed update when available.")
        task = (f"Confirm the next step for {job['title']} ({job_id}).\n"
                f"Owner: {job['owner'] or 'Unassigned'}\nBlocker: {job['blocker'] or 'Not recorded'}\n"
                f"Evidence: {job['evidence'] or 'Not recorded'}\n"
                f"Next step: {job['next_step'] or 'Verify the blocker and document a revised plan.'}")
        preview = f"CUSTOMER UPDATE\n{customer}\n\nINTERNAL FOLLOW-UP\n{task}\n\nSource: Data/jobs.json, record {job_id}."
        research = self.external(job, chat, get)
        if research:
            preview += research
        self.pending = (job_id, preview, root, hashlib.sha256(snapshot).hexdigest())
        return preview + f"\n\nSay approve drafts for job {job_id} to save both locally, or cancel drafts."
