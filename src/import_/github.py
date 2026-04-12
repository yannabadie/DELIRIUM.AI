"""GitHub Repository Importer — Decompose repos into semantic fragments.

Each repo is decomposed into sub-fragments via LLM summarization:
- PURPOSE: what the project does/solves (2-3 sentences)
- MODULES: key directories/components and what each does (max 5)
- PROBLEMS: open issues, TODOs, abandoned status

All fragments are natural language (Option C) for unified mpnet embedding.
Uses `gh` CLI for authenticated GitHub API access.
"""

import json
import logging
import subprocess
from base64 import b64decode

from src.import_.base import ImportedMessage
from src.llm_client import LLMClient
from src.config import MINIMAX_MODEL_FAST

logger = logging.getLogger("delirium.import.github")


class GitHubImporter:
    """Import GitHub repositories as semantic fragments for Cold Weaver."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def import_user(self, username: str) -> list[ImportedMessage]:
        """Fetch all repos for a user, decompose each into sub-fragments."""
        repos = self._fetch_repos(username)
        if not repos:
            logger.warning("No repos found for %s", username)
            return []

        logger.info("Found %d repos for %s", len(repos), username)
        all_messages = []

        for repo in repos:
            try:
                messages = self._decompose_repo(repo)
                all_messages.extend(messages)
                logger.info("  %s: %d fragments", repo["name"], len(messages))
            except Exception as e:
                logger.warning("Skipping %s: %s", repo["name"], e)

        logger.info("Total: %d fragments from %d repos", len(all_messages), len(repos))
        return all_messages

    def _fetch_repos(self, username: str) -> list[dict]:
        """Fetch repo list via gh CLI."""
        fields = "name,description,primaryLanguage,repositoryTopics,isArchived,updatedAt,owner"
        result = subprocess.run(
            ["gh", "repo", "list", username, "--limit", "100",
             "--json", fields, "--no-archived"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            logger.error("gh repo list failed: %s", result.stderr)
            return []

        repos = json.loads(result.stdout)
        # Normalize structure
        for repo in repos:
            repo["owner"] = repo.get("owner", {}).get("login", username)
            lang = repo.get("primaryLanguage")
            repo["language"] = lang.get("name", "") if isinstance(lang, dict) else ""
            topics_raw = repo.get("repositoryTopics") or []
            repo["topics"] = [t.get("name", "") if isinstance(t, dict) else str(t)
                              for t in topics_raw if t]
        return repos

    def _fetch_readme(self, owner: str, name: str) -> str:
        """Fetch README content via gh API."""
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{name}/readme", "--jq", ".content"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return ""
        try:
            content = b64decode(result.stdout.strip()).decode("utf-8", errors="replace")
            return content[:3000]  # cap for LLM context
        except Exception:
            return ""

    def _fetch_tree(self, owner: str, name: str) -> list[str]:
        """Fetch top-level directory/file names."""
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{name}/git/trees/HEAD",
             "--jq", '.tree[] | select(.type=="tree") | .path'],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

    def _fetch_issues(self, owner: str, name: str) -> list[str]:
        """Fetch open issue titles (max 10)."""
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{name}/issues?state=open&per_page=10",
             "--jq", ".[].title"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.strip().split("\n")
                if line.strip()][:10]

    def _decompose_repo(self, repo: dict) -> list[ImportedMessage]:
        """Generate PURPOSE + MODULES + PROBLEMS fragments via LLM."""
        owner = repo["owner"]
        name = repo["name"]
        readme = self._fetch_readme(owner, name)
        tree = self._fetch_tree(owner, name)
        issues = self._fetch_issues(owner, name)

        fragments = []

        # 1. PURPOSE
        purpose = self._generate_purpose(repo, readme)
        if purpose:
            fragments.append(self._to_message(repo, "PURPOSE", purpose))

        # 2. MODULES
        if tree:
            modules = self._generate_modules(repo, tree, readme)
            for mod_name, mod_desc in modules:
                fragments.append(self._to_message(repo, f"MODULE:{mod_name}", mod_desc))

        # 3. PROBLEMS
        problems = self._generate_problems(repo, issues, readme)
        if problems:
            fragments.append(self._to_message(repo, "PROBLEMS", problems))

        return fragments

    def _generate_purpose(self, repo: dict, readme: str) -> str:
        """LLM: summarize what the project does in natural language."""
        prompt = (
            "Résume ce projet GitHub en 2-3 phrases en français. "
            "Décris : quel PROBLÈME il résout, quelle APPROCHE il utilise, "
            "et ce qui le rend UNIQUE. Pas de jargon inutile.\n\n"
            f"Nom: {repo['name']}\n"
            f"Description: {repo.get('description', 'aucune')}\n"
            f"Langage: {repo.get('language', 'inconnu')}\n"
            f"Topics: {', '.join(repo.get('topics', []))}\n"
            f"README (extrait):\n{readme[:2000]}"
        )
        return self.llm.chat(
            system="Tu résumes des projets logiciels de manière concise et précise.",
            messages=[{"role": "user", "content": prompt}],
            model=MINIMAX_MODEL_FAST,
        )

    def _generate_modules(self, repo: dict, tree: list[str], readme: str) -> list[tuple[str, str]]:
        """LLM: identify key modules from directory structure."""
        prompt = (
            "Voici la structure d'un projet GitHub. Identifie les 3-5 modules/composants "
            "les plus importants. Pour chaque module, décris en 1-2 phrases ce qu'il fait.\n\n"
            f"Projet: {repo['name']} — {repo.get('description', '')}\n"
            f"Répertoires: {', '.join(tree[:20])}\n"
            f"README (extrait):\n{readme[:1500]}\n\n"
            'Réponds en JSON: [{"name": "module_name", "description": "ce que ça fait"}]'
        )
        raw = self.llm.chat(
            system="Tu analyses des projets logiciels. Réponds en JSON uniquement.",
            messages=[{"role": "user", "content": prompt}],
            model=MINIMAX_MODEL_FAST,
        )
        return self._parse_modules(raw)

    def _generate_problems(self, repo: dict, issues: list[str], readme: str) -> str:
        """LLM: summarize what's missing, broken, or abandoned."""
        if not issues and repo.get("updatedAt", "") > "2025-01-01":
            return ""  # active repo with no issues — nothing to report

        prompt = (
            "Décris en 2-3 phrases les PROBLÈMES ou LACUNES de ce projet. "
            "Qu'est-ce qui manque ? Qu'est-ce qui est cassé ou abandonné ?\n\n"
            f"Projet: {repo['name']} — {repo.get('description', '')}\n"
            f"Dernière mise à jour: {repo.get('updatedAt', 'inconnue')}\n"
            f"Issues ouvertes: {'; '.join(issues) if issues else 'aucune'}\n"
            f"README (extrait):\n{readme[:1000]}"
        )
        return self.llm.chat(
            system="Tu analyses les lacunes de projets logiciels. Sois direct.",
            messages=[{"role": "user", "content": prompt}],
            model=MINIMAX_MODEL_FAST,
        )

    def _to_message(self, repo: dict, fragment_type: str, content: str) -> ImportedMessage:
        return ImportedMessage(
            user_input=content,
            assistant_response=f"[GitHub: {repo['owner']}/{repo['name']} | {fragment_type}]",
            timestamp=repo.get("updatedAt", ""),
            source="github",
            conversation_title=f"{repo['name']}_{fragment_type}",
        )

    def _parse_modules(self, raw: str) -> list[tuple[str, str]]:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [(m["name"], m["description"]) for m in data[:5]
                        if isinstance(m, dict) and "name" in m and "description" in m]
        except (json.JSONDecodeError, KeyError):
            logger.warning("Failed to parse modules JSON")
        return []
