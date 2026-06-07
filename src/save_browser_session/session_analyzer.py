"""
Session analyzer module for generating smart session name suggestions.

This module analyzes browser tabs to suggest meaningful session names based on
domain frequency, keyword extraction, browsing patterns, and GitHub projects.
"""

import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Set
from urllib.parse import urlparse

from .browser import Tab, Window


@dataclass
class SessionNameSuggestion:
    """
    A suggested session name with confidence scoring and reasoning.

    Attributes:
        name: The suggested session name
        confidence: Confidence score from 0.0-1.0 (higher is better)
        reasoning: Explanation of why this name was suggested
        category: Type of suggestion (domain, keyword, pattern, github, history)
    """

    name: str
    confidence: float
    reasoning: str
    category: str


# Common English stop words to exclude from keyword analysis
STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "as",
    "is",
    "was",
    "are",
    "were",
    "been",
    "be",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "should",
    "could",
    "may",
    "might",
    "can",
    "this",
    "that",
    "these",
    "those",
    "what",
    "which",
    "who",
    "when",
    "where",
    "why",
    "how",
}


class SessionAnalyzer:
    """Analyzes browser sessions to generate smart name suggestions."""

    def __init__(self, windows: List[Window]):
        """
        Initialize analyzer with browser windows.

        Parameters:
            windows: List of browser windows containing tabs
        """
        self.windows = windows
        self.all_tabs = self._flatten_tabs()

    def _flatten_tabs(self) -> List[Tab]:
        """Flatten all tabs from all windows into a single list."""
        tabs: List[Tab] = []
        for window in self.windows:
            tabs.extend(window.tabs)
        return tabs

    def suggest_names(
        self, max_suggestions: int = 5, include_history: bool = True
    ) -> List[SessionNameSuggestion]:
        """
        Generate session name suggestions using multiple strategies.

        Parameters:
            max_suggestions: Maximum number of suggestions to return
            include_history: Whether to include historical session names

        Returns:
            List of suggestions sorted by confidence (highest first)
        """
        suggestions: List[SessionNameSuggestion] = []

        # Strategy 1: Domain frequency analysis
        suggestions.extend(self._suggest_from_domains())

        # Strategy 2: Keyword extraction from titles
        suggestions.extend(self._suggest_from_keywords())

        # Strategy 3: Browsing pattern detection
        suggestions.extend(self._suggest_from_patterns())

        # Strategy 4: GitHub project detection
        suggestions.extend(self._suggest_from_github())

        # Strategy 5: Historical session names
        if include_history:
            from .session_history import SessionHistory

            history = SessionHistory()
            historical_suggestions = history.get_suggestions(limit=3)
            suggestions.extend(historical_suggestions)

        # Deduplicate and sort by confidence
        suggestions = self._deduplicate_suggestions(suggestions)
        suggestions.sort(key=lambda s: s.confidence, reverse=True)

        return suggestions[:max_suggestions]

    def _suggest_from_domains(self) -> List[SessionNameSuggestion]:
        """Suggest names based on dominant domains."""
        if not self.all_tabs:
            return []

        domains: List[str] = []
        for tab in self.all_tabs:
            try:
                if not tab.url:
                    continue
                domain = urlparse(tab.url).netloc
                # Remove www. prefix
                domain = domain.replace("www.", "")
                if domain:
                    domains.append(domain)
            except Exception:
                continue

        if not domains:
            return []

        counter = Counter[str](domains)
        total = len(domains)
        suggestions: List[SessionNameSuggestion] = []

        # Get top domain
        top_domain, count = counter.most_common(1)[0]
        frequency = count / total

        # Only suggest if domain represents significant portion (40% threshold)
        if frequency >= 0.4:
            # Convert domain to friendly name
            friendly_name = self._domain_to_friendly_name(top_domain)
            confidence = min(frequency, 0.95)  # Cap at 0.95

            suggestions.append(
                SessionNameSuggestion(
                    name=friendly_name,
                    confidence=confidence,
                    reasoning=f"{count}/{total} tabs from {top_domain}",
                    category="domain",
                )
            )

        return suggestions

    def _domain_to_friendly_name(self, domain: str) -> str:
        """Convert domain to friendly session name."""
        # Remove TLD
        name = domain.rsplit(".", 1)[0]

        # Special cases for common domains
        domain_map = {
            "github": "GitHub",
            "stackoverflow": "Stack Overflow",
            "youtube": "YouTube",
            "reddit": "Reddit",
            "wikipedia": "Wikipedia",
            "twitter": "Twitter/X",
            "x": "Twitter/X",
            "linkedin": "LinkedIn",
            "medium": "Medium",
            "arxiv": "arXiv",
            "docs.python": "Python Docs",
            "developer.mozilla": "MDN",
        }

        name_lower = name.lower()
        if name_lower in domain_map:
            return f"{domain_map[name_lower]} Session"

        # Default: capitalize first letter
        return f"{name.capitalize()} Session"

    def _suggest_from_keywords(self) -> List[SessionNameSuggestion]:
        """Extract keywords from tab titles to suggest names."""
        words: List[str] = []
        for tab in self.all_tabs:
            if not tab.title:
                continue
            # Clean title and extract words (3+ characters)
            title_words = re.findall(r"\b[a-zA-Z]{3,}\b", tab.title.lower())
            words.extend([w for w in title_words if w not in STOP_WORDS])

        if len(words) < 3:
            return []

        # Count word frequency
        counter = Counter(words)

        # Get top 3 most common words
        top_words: List[str] = [word for word, _ in counter.most_common(3)]

        # Calculate confidence based on frequency
        total_words = len(words)
        top_word_count = sum(counter[w] for w in top_words[:2])
        confidence = min((top_word_count / total_words) * 1.5, 0.85)

        # Create a title-case name from top keywords
        name = " ".join(word.capitalize() for word in top_words[:2])

        return [
            SessionNameSuggestion(
                name=name,
                confidence=confidence,
                reasoning=f"Common keywords in {len(self.all_tabs)} tab titles",
                category="keyword",
            )
        ]

    def _suggest_from_patterns(self) -> List[SessionNameSuggestion]:
        """Detect common browsing patterns."""
        suggestions: List[SessionNameSuggestion] = []

        if not self.all_tabs:
            return []

        total_tabs = len(self.all_tabs)

        # Development pattern
        dev_domains = {
            "github.com",
            "stackoverflow.com",
            "stackexchange.com",
            "docs.python.org",
            "developer.mozilla.org",
            "devdocs.io",
        }
        dev_count = sum(
            1
            for tab in self.all_tabs
            if tab.url and any(d in tab.url for d in dev_domains)
        )

        if dev_count >= total_tabs * 0.5:  # 50% threshold
            suggestions.append(
                SessionNameSuggestion(
                    name="Development Session",
                    confidence=0.75,
                    reasoning=f"{dev_count} development-related tabs detected",
                    category="pattern",
                )
            )

        # Research pattern
        research_domains = {
            "wikipedia.org",
            "scholar.google",
            "arxiv.org",
            ".edu",
            "researchgate.net",
        }
        research_count = sum(
            1
            for tab in self.all_tabs
            if tab.url and any(d in tab.url for d in research_domains)
        )

        if research_count >= total_tabs * 0.4:  # 40% threshold
            suggestions.append(
                SessionNameSuggestion(
                    name="Research Session",
                    confidence=0.70,
                    reasoning=f"{research_count} research-related tabs detected",
                    category="pattern",
                )
            )

        return suggestions

    def _suggest_from_github(self) -> List[SessionNameSuggestion]:
        """Detect GitHub repository names."""
        github_pattern = re.compile(r"github\.com/([^/]+)/([^/]+)")
        repos: List[str] = []

        for tab in self.all_tabs:
            if not tab.url:
                continue
            match = github_pattern.search(tab.url)
            if match:
                owner, repo = match.groups()
                repos.append(f"{owner}/{repo}")

        if not repos:
            return []

        # Find most common repo
        counter = Counter[str](repos)
        top_repo, count = counter.most_common(1)[0]

        # Only suggest if we have multiple tabs from same repo
        if count >= 2:
            repo_name = top_repo.split("/")[1]
            confidence = min(0.80, 0.5 + (count / len(self.all_tabs)))

            return [
                SessionNameSuggestion(
                    name=f"{repo_name} Development",
                    confidence=confidence,
                    reasoning=f"{count} tabs from GitHub repo: {top_repo}",
                    category="github",
                )
            ]

        return []

    def _deduplicate_suggestions(
        self, suggestions: List[SessionNameSuggestion]
    ) -> List[SessionNameSuggestion]:
        """Remove duplicate or very similar suggestions."""
        seen_names: Set[str] = set()
        unique: List[SessionNameSuggestion] = []

        for suggestion in suggestions:
            name_lower = suggestion.name.lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique.append(suggestion)

        return unique
