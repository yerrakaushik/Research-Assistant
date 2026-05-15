"""
arxiv_search.py – searches ArXiv for relevant research papers.
Uses the `arxiv` Python library (no API key required).
"""

import arxiv
from typing import List, Dict
import re


def search_arxiv(query: str, max_results: int = 8) -> List[Dict]:
    """
    Search ArXiv for papers matching the query.
    Returns a list of dicts with paper metadata.
    """
    client = arxiv.Client(num_retries=3, delay_seconds=2)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    papers = []
    try:
        for result in client.results(search):
            papers.append({
                "title": result.title,
                "authors": [a.name for a in result.authors[:5]],
                "abstract": result.summary[:800],
                "url": result.entry_id,
                "published": result.published.strftime("%Y-%m-%d") if result.published else "Unknown",
            })
    except Exception as e:
        print(f"[ArXiv] Search error: {e}")

    return papers
