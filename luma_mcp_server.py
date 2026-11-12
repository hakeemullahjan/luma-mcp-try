#!/usr/bin/env python3
"""
Luma MCP Server (Paris & Worldwide Events)
Provides Model Context Protocol (MCP) tools for discovering and searching events on Lu.ma.
"""

import json
import urllib.request
import urllib.parse
from typing import Optional, List, Dict, Any
from mcp.server.mcpserver import MCPServer

# Initialize MCP Server
mcp = MCPServer("luma-paris-mcp")

PARIS_COORDS = {"latitude": 48.8566, "longitude": 2.3522}

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "x-luma-client-type": "luma-web",
    "Referer": "https://luma.com/paris",
    "Origin": "https://luma.com",
}


def _prose_mirror_to_text(node: Any) -> str:
    """Recursively converts Lu.ma ProseMirror description to plain readable text."""
    if not node or not isinstance(node, dict):
        return ""
    node_type = node.get("type", "")
    if node_type == "text":
        return node.get("text", "")
    if node_type == "hard_break":
        return "\n"
    content = node.get("content", [])
    children = "".join(_prose_mirror_to_text(child) for child in content)
    if node_type == "paragraph":
        return children + "\n"
    if node_type == "heading":
        level = node.get("attrs", {}).get("level", 1)
        return "#" * level + " " + children + "\n"
    if node_type == "bullet_list":
        return "".join("- " + _prose_mirror_to_text(li).strip() + "\n" for li in content)
    if node_type == "ordered_list":
        return "".join(f"{i+1}. " + _prose_mirror_to_text(li).strip() + "\n" for i, li in enumerate(content))
    return children


def _fetch_luma_events(
    lat: float = PARIS_COORDS["latitude"],
    lon: float = PARIS_COORDS["longitude"],
    slug: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    query_params = {
        "latitude": str(lat),
        "longitude": str(lon),
        "pagination_limit": str(min(limit, 50)),
    }
    if slug:
        query_params["slug"] = slug
    if cursor:
        query_params["pagination_cursor"] = cursor

    url = f"https://api.luma.com/discover/get-paginated-events?{urllib.parse.urlencode(query_params)}"
    req = urllib.request.Request(url, headers=COMMON_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"entries": [], "has_more": False, "error": str(e)}


def _format_event_entry(item: Dict[str, Any]) -> Dict[str, Any]:
    ev = item.get("event", {})
    geo = ev.get("geo_address_info") or {}
    full_address = geo.get("full_address") or geo.get("address") or geo.get("city") or "Paris, France"
    ticket_info = item.get("ticket_info") or {}
    is_free = ticket_info.get("is_free", True)
    hosts = [h.get("name") for h in item.get("hosts", []) if h.get("name")]
    
    return {
        "event_api_id": ev.get("api_id"),
        "title": ev.get("name") or "Untitled Event",
        "url": f"https://luma.com/{ev.get('url', '')}",
        "start_at": ev.get("start_at"),
        "end_at": ev.get("end_at"),
        "timezone": ev.get("timezone", "Europe/Paris"),
        "location": full_address,
        "is_free": is_free,
        "hosts": ", ".join(hosts) if hosts else "Not specified",
        "calendar": item.get("calendar", {}).get("name", "N/A"),
    }


@mcp.tool()
def get_paris_events(
    category: Optional[str] = None,
    limit: int = 10,
) -> str:
    """
    Get upcoming events in Paris from Lu.ma.

    Args:
        category: Optional category filter like 'ai', 'tech', 'crypto', 'design', 'founders'.
        limit: Number of events to retrieve (default: 10, max: 25).

    Returns:
        A list of formatted Paris events with title, date, location, url, and free/paid status.
    """
    data = _fetch_luma_events(slug=category, limit=limit)
    entries = data.get("entries", [])
    if not entries:
        return f"No events found for Paris with category '{category}'."

    formatted = [_format_event_entry(item) for item in entries[:limit]]
    return json.dumps(formatted, indent=2, ensure_ascii=False)


@mcp.tool()
def search_paris_events(
    keyword: str,
    limit: int = 10,
) -> str:
    """
    Search upcoming events in Paris by keyword in their title, description, or hosts.

    Args:
        keyword: Search query (e.g. 'hackathon', 'ai', 'networking', 'workshop', 'co-working').
        limit: Maximum results to return (default: 10).

    Returns:
        JSON list of events matching the keyword.
    """
    # Fetch a broader batch to filter locally
    data = _fetch_luma_events(limit=50)
    entries = data.get("entries", [])
    kw = keyword.lower().strip()

    matches = []
    for item in entries:
        ev = item.get("event", {})
        title = (ev.get("name") or "").lower()
        hosts = " ".join([h.get("name", "").lower() for h in item.get("hosts", [])])
        cal = (item.get("calendar", {}).get("name") or "").lower()

        if kw in title or kw in hosts or kw in cal:
            matches.append(_format_event_entry(item))
            if len(matches) >= limit:
                break

    if not matches:
        return f"No upcoming events found in Paris matching '{keyword}'."

    return json.dumps(matches, indent=2, ensure_ascii=False)


@mcp.tool()
def get_event_details(event_api_id: str) -> str:
    """
    Get detailed information about a specific Lu.ma event including its full description and ticket info.

    Args:
        event_api_id: The unique API ID of the event (e.g. 'evt-AAtD0zByXyI163o').

    Returns:
        Detailed JSON event information.
    """
    url = f"https://api.luma.com/event/get?event_api_id={urllib.parse.quote(event_api_id)}"
    req = urllib.request.Request(url, headers=COMMON_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return f"Failed to fetch event details for {event_api_id}: {str(e)}"

    ev = data.get("event", {})
    desc_node = data.get("description_mirror")
    description = _prose_mirror_to_text(desc_node).strip() if desc_node else "No description available."
    ticket_types = data.get("ticket_types", [])
    ticket_summary = []
    for t in ticket_types:
        price = "Free" if t.get("type") == "free" or t.get("cents") is None else f"${t.get('cents', 0)/100:.2f}"
        ticket_summary.append(f"{t.get('name', 'Standard')}: {price}")

    details = {
        "event_api_id": ev.get("api_id"),
        "title": ev.get("name"),
        "url": f"https://luma.com/{ev.get('url', '')}",
        "start_at": ev.get("start_at"),
        "end_at": ev.get("end_at"),
        "timezone": ev.get("timezone"),
        "location": ev.get("geo_address_info", {}).get("full_address", "Paris, France"),
        "tickets": ticket_summary or ["Free"],
        "description": description[:1500] + ("..." if len(description) > 1500 else ""),
    }

    return json.dumps(details, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
