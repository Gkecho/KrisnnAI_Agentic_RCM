"""How a portal bot looks at a page: fetch, then read elements by id. No browser needed for server-rendered portals.

`HttpDriver` is the default and the guaranteed path. A browser driver (Playwright) can implement the same three
methods for portals that need JavaScript; it is optional and not installed by default.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

from krisnai.integrations.clearinghouse.client import check_endpoint


class ScreenChanged(Exception):
    """A page does not have the elements the bot was written for. The bot stops and hands over to a person."""

    def __init__(self, page: str, missing: list[str]):
        super().__init__(f"{page}: expected element(s) not found: {', '.join(missing)}")
        self.page, self.missing = page, missing


class _Ids(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: dict[str, str] = {}
        self._open: list[str] = []
        self.links: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        d = dict(attrs)
        if "id" in d:
            self.text.setdefault(d["id"], "")
            self._open.append(d["id"])
            if tag == "a" and "href" in d:
                self.links[d["id"]] = d["href"]
        else:
            self._open.append("")

    def handle_endtag(self, tag):  # noqa: ANN001
        if self._open:
            self._open.pop()

    def handle_data(self, data):  # noqa: ANN001
        for ident in self._open:
            if ident:
                self.text[ident] += data


@dataclass
class Page:
    url: str
    status: int
    html: str

    def _parse(self) -> _Ids:
        if not hasattr(self, "_p"):
            p = _Ids()
            p.feed(self.html)
            self._p = p
        return self._p

    def ids(self) -> set[str]:
        return set(self._parse().text)

    def text(self, ident: str) -> str:
        return " ".join(self._parse().text.get(ident, "").split())

    def link(self, ident: str) -> str:
        return self._parse().links.get(ident, "")

    def require(self, name: str, ids: list[str]) -> None:
        missing = [i for i in ids if i not in self.ids()]
        if missing:
            raise ScreenChanged(name, missing)


class HttpDriver:
    def __init__(self, base_url: str, client: httpx.Client | None = None, delay: float = 0.0):
        check_endpoint(base_url)
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(base_url=self.base_url, timeout=30, follow_redirects=True)
        self.delay = delay
        self.requests = 0

    def _go(self, method: str, path: str, **kw) -> Page:
        if self.delay:
            time.sleep(self.delay)
        self.requests += 1
        r = self.client.request(method, path, **kw)
        return Page(str(r.url), r.status_code, r.text)

    def get(self, path: str, params: dict | None = None) -> Page:
        return self._go("GET", path, params=params)

    def post(self, path: str, data: dict) -> Page:
        return self._go("POST", path, data=data)

    def close(self) -> None:
        self.client.close()
