
from crewai.tools import tool
from ddgs import DDGS


@tool("web_search")
def web_search(query: str) -> str:
    """Search the web using a plain-text query. Input must contain only query."""

    if not isinstance(query, str) or not query.strip():
        return "Please provide a search query."

    try:
        results = DDGS().text(query.strip(), max_results=5)

        if not results:
            return "No search results found."

        return "\n\n".join(
            f"Title: {item.get('title', '')}\n"
            f"URL: {item.get('href', '')}\n"
            f"Summary: {item.get('body', '')}"
            for item in results
        )

    except Exception as exc:
        return f"Web search failed: {exc}"
