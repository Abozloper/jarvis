"""Source-backed answers for the US Netflix monthly release calendar."""
import re
from datetime import date, timedelta
from html.parser import HTMLParser

import requests


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading = ""
        self.tag = ""
        self.parts = []
        self.day = None
        self.movies = []

    def handle_starttag(self, tag, attrs):
        if tag in {"h2", "h3", "h4", "li"}:
            self.tag, self.parts = tag, []

    def handle_data(self, data):
        if self.tag:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if self.tag != tag:
            return
        value = " ".join("".join(self.parts).split())
        self.tag, self.parts = "", []
        if tag.startswith("h"):
            self.day = re.search(r"coming to netflix on (\w+ \d{1,2})", value, re.I)
        elif self.day:
            name = re.match(r"^(.{1,180}?)\s*\(\d{4}\)(.*)$", value)
            if name and not re.search(r"\blive event\b", name[2], re.I):
                self.movies.append((name[1].strip(), self.day[1]))


def answer(text, today=None, get=requests.get):
    words = text.casefold()
    if (not re.search(r"\bnetflix\b", words)
            or not re.search(r"\b(?:movies|films)\b", words)
            or not re.search(r"\bnext month\b", words)
            or not re.search(r"\b(?:coming|releases?|out|added|new)\b", words)
            or re.match(r"^\s*(?:open|play|launch|search google)\b", words)):
        return None
    if re.search(r"\b(?:colombia|canada|uk|australia|india|global|worldwide)\b", words):
        return "I can currently verify this monthly Netflix list for the US catalog only."
    count = re.search(r"\b(\d{1,2})\b", words)
    limit = min(20, max(1, int(count[1]))) if count else 10
    today = today or date.today()
    month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    label = month.strftime("%B %Y")
    url = ("https://www.whats-on-netflix.com/coming-soon/whats-coming-to-netflix-in-"
           + label.lower().replace(" ", "-") + "/")
    calendar = Calendar()
    try:
        with get(url, timeout=(4, 8), stream=True, allow_redirects=False) as response:
            if response.status_code != 200:
                return f"I couldn't verify Netflix's US movie listings for {label}."
            size = 0
            for chunk in response.iter_content(65536, decode_unicode=False):
                size += len(chunk)
                if size > 4_000_000:
                    break
                calendar.feed(chunk.decode("utf-8", errors="replace"))
    except requests.RequestException:
        return f"I couldn't reach the Netflix release calendar for {label}."
    movies = list(dict.fromkeys((title, day) for title, day in calendar.movies
                                if day.split()[0].casefold() == month.strftime("%B").casefold()))[:limit]
    if not movies:
        return f"I found no dated US Netflix movie listings I could verify for {label}."
    lines = [f"{len(movies)} upcoming Netflix US movies for {label}, in release order:"]
    lines += [f"{i}. {title} — {day}" for i, (title, day) in enumerate(movies, 1)]
    return "\n".join(lines) + "\nSource: What's on Netflix — " + url
