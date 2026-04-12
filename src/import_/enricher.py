"""Fragment Enricher — Fetch content from URLs/repos mentioned in messages.

When a user mentions a GitHub repo, a website, or an ArXiv paper,
the enricher fetches a summary of the actual content. This summary
is appended to the message text BEFORE embedding, so the vector
captures what the link is ABOUT, not just that a link was mentioned.

This makes collisions between "Analyse ce repo X" and "Analyse ce repo Y"
actually reflect the difference between X and Y.
"""

import logging
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser

logger = logging.getLogger("delirium.import.enricher")

# URL detection regex
_URL_RE = re.compile(
    r'https?://[^\s<>\"\'\)]+',
    re.IGNORECASE,
)

# GitHub repo pattern: github.com/owner/repo
_GITHUB_RE = re.compile(
    r'github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)',
    re.IGNORECASE,
)

# ArXiv pattern
_ARXIV_RE = re.compile(
    r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})',
    re.IGNORECASE,
)

_HEADERS = {"User-Agent": "Delirium-AI/0.1"}
_TIMEOUT = 10


class _TitleParser(HTMLParser):
    """Minimal HTML parser that extracts <title> and meta description."""

    def __init__(self):
        super().__init__()
        self._in_title = False
        self.title = ""
        self.description = ""

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            attrs_dict = dict(attrs)
            name = attrs_dict.get("name", "").lower()
            if name in ("description", "og:description"):
                self.description = attrs_dict.get("content", "")[:300]

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


def extract_urls(text: str) -> list[str]:
    """Extract all URLs from text."""
    return _URL_RE.findall(text)


def enrich_text(text: str) -> str:
    """Enrich text by fetching summaries of any URLs/repos mentioned.

    Returns the original text + appended summaries.
    Failures are silently skipped (best-effort).
    """
    urls = extract_urls(text)
    if not urls:
        return text

    enrichments = []
    seen = set()

    for url in urls[:3]:  # max 3 URLs per message
        if url in seen:
            continue
        seen.add(url)

        summary = _fetch_summary(url)
        if summary:
            enrichments.append(summary)

    if not enrichments:
        return text

    return text + "\n\n[Contenu des liens:]\n" + "\n".join(enrichments)


def _fetch_summary(url: str) -> str | None:
    """Fetch a short summary of a URL. Returns None on failure."""
    try:
        # GitHub repo
        gh_match = _GITHUB_RE.search(url)
        if gh_match:
            return _fetch_github(gh_match.group(1))

        # ArXiv paper
        arxiv_match = _ARXIV_RE.search(url)
        if arxiv_match:
            return _fetch_arxiv(arxiv_match.group(1))

        # Generic webpage
        return _fetch_webpage(url)

    except Exception as e:
        logger.debug("Failed to enrich %s: %s", url[:60], e)
        return None


def _fetch_github(repo_path: str) -> str | None:
    """Fetch GitHub repo description and language via API."""
    api_url = f"https://api.github.com/repos/{repo_path}"
    req = urllib.request.Request(api_url, headers={
        **_HEADERS,
        "Accept": "application/vnd.github.v3+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            import json
            data = json.loads(resp.read())

        parts = [f"[GitHub: {repo_path}]"]
        if data.get("description"):
            parts.append(data["description"])
        if data.get("language"):
            parts.append(f"Language: {data['language']}")
        topics = data.get("topics", [])
        if topics:
            parts.append(f"Topics: {', '.join(topics[:5])}")

        return " | ".join(parts)
    except urllib.error.HTTPError:
        return f"[GitHub: {repo_path}]"


def _fetch_arxiv(paper_id: str) -> str | None:
    """Fetch ArXiv paper title and abstract."""
    import xml.etree.ElementTree as ET
    api_url = f"http://export.arxiv.org/api/query?id_list={paper_id}"
    req = urllib.request.Request(api_url, headers=_HEADERS)

    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        root = ET.fromstring(resp.read())

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        return None

    title = (entry.findtext("atom:title", "", ns) or "").strip().replace("\n", " ")
    summary = (entry.findtext("atom:summary", "", ns) or "").strip().replace("\n", " ")

    return f"[ArXiv: {paper_id}] {title}. {summary[:300]}"


def _fetch_webpage(url: str) -> str | None:
    """Fetch webpage title and meta description."""
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            # Only read first 50KB to avoid large pages
            content = resp.read(50000)
            charset = resp.headers.get_content_charset() or "utf-8"
            html = content.decode(charset, errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, UnicodeDecodeError):
        return None

    parser = _TitleParser()
    try:
        parser.feed(html)
    except Exception:
        return None

    parts = []
    if parser.title:
        parts.append(f"[Web: {parser.title.strip()[:100]}]")
    if parser.description:
        parts.append(parser.description)

    return " ".join(parts) if parts else None
