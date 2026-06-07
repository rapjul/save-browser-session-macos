from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List

import pytest

from save_browser_session.browser import Tab, Window
from save_browser_session.session_analyzer import SessionAnalyzer

if TYPE_CHECKING:
    from save_browser_session.session_analyzer import SessionNameSuggestion


# Mock structures for testing
@dataclass
class MockTab(Tab):
    url: str
    title: str
    id: str | None = None


@dataclass
class MockWindow(Window):
    def __init__(self, tabs: List[Any]):
        # We only need tabs for analyzer testing
        self.tabs = tabs
        self.id = 1
        self.os_id = 1


@pytest.fixture
def empty_analyzer() -> SessionAnalyzer:
    return SessionAnalyzer([])


def test_init(empty_analyzer: SessionAnalyzer) -> None:
    assert empty_analyzer.windows == []
    assert empty_analyzer.all_tabs == []


def test_flatten_tabs() -> None:
    w1 = MockWindow([MockTab(url="u1", title="t1")])
    w2 = MockWindow([MockTab(url="u2", title="t2"), MockTab(url="u3", title="t3")])
    analyzer = SessionAnalyzer([w1, w2])

    assert len(analyzer.all_tabs) == 3
    assert analyzer.all_tabs[0].url == "u1"
    assert analyzer.all_tabs[2].url == "u3"


def test_suggest_from_domains() -> None:
    # Setup tabs where google.com is dominant (3/4)
    tabs = [
        MockTab(url="https://google.com/search?q=1", title="Google 1"),
        MockTab(url="https://google.com/search?q=2", title="Google 2"),
        MockTab(url="https://www.google.com/maps", title="Google Maps"),
        MockTab(url="https://example.com", title="Example"),
    ]
    window = MockWindow(tabs)
    analyzer = SessionAnalyzer([window])

    suggestions: List[SessionNameSuggestion] = analyzer._suggest_from_domains()  # type: ignore[protected-access]

    assert len(suggestions) == 1
    assert suggestions[0].name == "Google Session"
    assert suggestions[0].category == "domain"
    assert suggestions[0].confidence >= 0.75  # 3/4 frequency


def test_suggest_from_domains_no_dominant() -> None:
    # No domain reaches 40% threshold
    tabs = [
        MockTab(url="https://a.com", title="A"),
        MockTab(url="https://b.com", title="B"),
        MockTab(url="https://c.com", title="C"),
    ]
    window = MockWindow(tabs)
    analyzer = SessionAnalyzer([window])

    suggestions = analyzer._suggest_from_domains()  # type: ignore[protected-access]
    assert len(suggestions) == 0


def test_domain_friendly_names() -> None:
    analyzer = SessionAnalyzer([])

    assert analyzer._domain_to_friendly_name("github.com") == "GitHub Session"  # type: ignore[protected-access]
    assert (
        analyzer._domain_to_friendly_name("stackoverflow.com")
        == "Stack Overflow Session"
    )  # type: ignore[protected-access]
    assert analyzer._domain_to_friendly_name("docs.python.org") == "Python Docs Session"  # type: ignore[protected-access]
    assert (
        analyzer._domain_to_friendly_name("unknown-site.com") == "Unknown-site Session"
    )  # type: ignore[protected-access]


def test_suggest_from_keywords() -> None:
    # "Python" and "Programming" appear frequently
    tabs = [
        MockTab(url="u1", title="Python Programming Guide"),
        MockTab(url="u2", title="Advanced Python Programming"),
        MockTab(url="u3", title="Python Tutorial"),
    ]
    window = MockWindow(tabs)
    analyzer = SessionAnalyzer([window])

    suggestions = analyzer._suggest_from_keywords()  # type: ignore[protected-access]

    assert len(suggestions) == 1
    # Should pick "Python" and "Programming"
    assert "Python" in suggestions[0].name
    assert "Programming" in suggestions[0].name
    assert suggestions[0].category == "keyword"


def test_suggest_from_keywords_insufficient_data() -> None:  # type: ignore[protected-access]
    tabs = [
        MockTab(url="u1", title="One"),
        MockTab(url="u2", title="Two"),
    ]
    window = MockWindow(tabs)
    analyzer = SessionAnalyzer([window])

    suggestions: List[SessionNameSuggestion] = analyzer._suggest_from_keywords()  # type: ignore[protected-access]
    assert len(suggestions) == 0


def test_suggest_from_patterns_development() -> None:
    tabs = [  # type: ignore[protected-access]
        MockTab(url="https://github.com/foo/bar", title="GitHub"),
        MockTab(url="https://stackoverflow.com/questions/1", title="SO"),
        MockTab(url="https://docs.python.org/3/", title="Docs"),
    ]
    window = MockWindow(tabs)
    analyzer = SessionAnalyzer([window])

    suggestions: List[SessionNameSuggestion] = analyzer._suggest_from_patterns()  # type: ignore[protected-access]

    assert len(suggestions) == 1
    assert suggestions[0].name == "Development Session"
    assert suggestions[0].category == "pattern"


def test_suggest_from_patterns_research() -> None:  # type: ignore[protected-access]
    tabs = [
        MockTab(url="https://wikipedia.org/wiki/AI", title="Wiki"),
        MockTab(url="https://arxiv.org/abs/1234.5678", title="ArXiv"),
    ]
    window = MockWindow(tabs)
    analyzer = SessionAnalyzer([window])

    suggestions: List[SessionNameSuggestion] = analyzer._suggest_from_patterns()  # type: ignore[protected-access]

    assert len(suggestions) == 1
    assert suggestions[0].name == "Research Session"
    assert suggestions[0].category == "pattern"


def test_suggest_from_github() -> None:
    tabs = [
        MockTab(url="https://github.com/user/project/issues", title="Issues"),
        MockTab(url="https://github.com/user/project/pulls", title="PRs"),
        MockTab(url="https://github.com/other/repo", title="Other"),
    ]
    window = MockWindow(tabs)
    analyzer = SessionAnalyzer([window])

    suggestions: List[SessionNameSuggestion] = analyzer._suggest_from_github()  # type: ignore[protected-access]

    assert len(suggestions) == 1
    assert suggestions[0].name == "project Development"
    assert "user/project" in suggestions[0].reasoning
    assert suggestions[0].category == "github"


def test_deduplication_and_sorting() -> None:
    tabs = [
        MockTab(url="https://github.com/user/project", title="Project"),
        MockTab(url="https://github.com/user/project", title="Project"),
    ]
    window = MockWindow(tabs)
    analyzer = SessionAnalyzer([window])

    # Analyze should call all strategies and merge
    suggestions = analyzer.suggest_names(include_history=False)

    # Should handle duplicates if multiple strategies return same name
    # (Though in this mocked case strategies likely return different names,
    # but let's verify we get a sorted list back)

    assert isinstance(suggestions, list)
    # Verify sorting by confidence
    if len(suggestions) > 1:
        assert suggestions[0].confidence >= suggestions[1].confidence
