from __future__ import annotations

from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from xml.etree import ElementTree


def fetch_news(symbol: str, limit: int = 8) -> list[dict[str, str]]:
    query = quote_plus(f'"{symbol}" stock')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    request = Request(url, headers={"User-Agent": "TradingMultiAgent/1.0"})
    with urlopen(request, timeout=8) as response:
        root = ElementTree.fromstring(response.read())

    items: list[dict[str, str]] = []
    for item in root.findall("./channel/item")[: max(0, limit)]:
        items.append(
            {
                "title": item.findtext("title", default=""),
                "published": item.findtext("pubDate", default=""),
                "link": item.findtext("link", default=""),
            }
        )
    return items