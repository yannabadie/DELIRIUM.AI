"""External sources for Cold Weaver — ArXiv API for MVP.

Fetches recent papers matching active themes.
"""

import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("delirium.cold_weaver.sources")


@dataclass
class ExternalFragment:
    """A piece of external content fetched by Cold Weaver."""
    title: str
    summary: str
    source: str       # "arxiv"
    url: str
    published: str
    query_theme: str  # the theme that triggered this fetch


class ArxivSource:
    """Fetch recent ArXiv papers matching themes."""

    ARXIV_API = "http://export.arxiv.org/api/query"

    def fetch(self, themes: list[str], max_results_per_theme: int = 3) -> list[ExternalFragment]:
        """Fetch papers for the given themes."""
        results = []

        for theme in themes[:5]:  # max 5 themes
            try:
                fragments = self._query_arxiv(theme, max_results_per_theme)
                results.extend(fragments)
            except Exception as e:
                logger.warning("ArXiv query failed for '%s': %s", theme, e)

        logger.info("Fetched %d ArXiv papers for %d themes", len(results), len(themes))
        return results

    def _query_arxiv(self, theme: str, max_results: int) -> list[ExternalFragment]:
        query = urllib.parse.quote(theme)
        url = f"{self.ARXIV_API}?search_query=all:{query}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"

        req = urllib.request.Request(url, headers={"User-Agent": "Delirium-AI/0.1"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        fragments = []
        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
            summary = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")
            published = entry.findtext("atom:published", "", ns)
            link = ""
            for l in entry.findall("atom:link", ns):
                if l.get("type") == "text/html":
                    link = l.get("href", "")
                    break
            if not link:
                link_el = entry.find("atom:id", ns)
                link = link_el.text if link_el is not None else ""

            if title and summary:
                fragments.append(ExternalFragment(
                    title=title[:200],
                    summary=summary[:500],
                    source="arxiv",
                    url=link,
                    published=published,
                    query_theme=theme,
                ))

        return fragments
