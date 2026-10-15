"""The web sources shown with a medicine explanation or a clash alert: one shape, stored and served the same way.

A source is {"title": site name, "url": link}. The title is the site's name ("drugs.com", "nhs.uk"), never a page title or a redirect.
The url is "" when there is no page to open. Grounded sources keep Google's redirect link: it opens the real page, and the screen says
so ("drugs.com, opens via Google"). Drug-label data from openFDA is a query to an API, not a page, so it has no link and the screen shows
its name as plain text.

Rows saved before this shape (a "www." title, an openFDA query address, the older openFDA title) are cleaned the same way when they are
read, so nothing needs migrating. Each site is shown once, by its site name. Nothing here calls a model or the database.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

OPENFDA_TITLE = "Drug label data (openFDA)"
REDIRECT_HOST = "vertexaisearch.cloud.google.com"
_DOMAIN = re.compile(r"^(?:[a-z0-9-]+\.)+[a-z]{2,}$")


def host_of(url: object) -> str:
    try:
        return (urlsplit(str(url or "")).hostname or "").lower()
    except ValueError:
        return ""


def is_web_link(url: object) -> bool:
    return str(url or "").lower().startswith(("https://", "http://")) and bool(host_of(url))


def is_openfda(title: object, url: object) -> bool:
    return host_of(url).endswith("api.fda.gov") or "openfda" in str(title or "").lower()


def site_name(title: object, url: object) -> str:
    """The site's name: the title when it is a domain, else the host of a real page, else the title as it is."""
    plain = " ".join(str(title or "").split())
    t = plain.lower().removeprefix("www.")
    if _DOMAIN.match(t):
        return t
    host = host_of(url).removeprefix("www.")
    if host and not host.endswith(REDIRECT_HOST):
        return host
    return plain[:120] or "Web page"


def clean(sources: Iterable[Mapping[str, Any]] | None) -> list[dict[str, str]]:
    """The stored and served shape: one entry per site, in the order given, each with a title and a link ("" when there is none)."""
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for s in sources or []:
        title, url = s.get("title"), s.get("url")
        if is_openfda(title, url):
            name, link = OPENFDA_TITLE, ""
        else:
            name, link = site_name(title, url), (str(url) if is_web_link(url) else "")
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append({"title": name, "url": link})
    return out
