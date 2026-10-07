"""Official arXiv and Crossref metadata adapters.

Adapters parse provider observations, never infer scientific coverage or reading.
"""
from __future__ import annotations
import hashlib
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET

class ProviderError(ValueError):
    pass

def normalize_identifier(value: str) -> tuple[str, str]:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ProviderError("identifier must contain 1-512 characters")
    value = value.strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    value = re.sub(r"^doi:\s*", "", value, flags=re.I)
    if re.match(r"^10\.\d{4,9}/\S+$", value, re.I) and not re.search(r"[\x00-\x20<>]", value):
        return "doi", value.lower()
    value = re.sub(r"^https?://(?:www\.)?arxiv\.org/(?:abs|pdf|html)/", "", value, flags=re.I)
    value = re.sub(r"^arxiv:\s*", "", value, flags=re.I)
    value = re.sub(r"\.pdf$", "", value, flags=re.I)
    if re.match(r"^(?:\d{4}\.\d{4,5}|[a-z][a-z.\-]+/\d{7})(?:v[1-9]\d*)?$", value, re.I):
        return "arxiv", value
    raise ProviderError("identifier must be a valid DOI or arXiv ID")

def paper_id(kind: str, identity: str) -> str:
    return "P-" + hashlib.sha256((kind + ":" + identity).encode("utf-8")).hexdigest()[:16]

def arxiv_papers(body: bytes) -> tuple[list[dict], int | None]:
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise ProviderError("arXiv XML cannot contain document type/entity declarations")
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ProviderError("malformed arXiv Atom response") from exc
    ns = {"atom": "http://www.w3.org/2005/Atom", "open": "http://a9.com/-/spec/opensearch/1.1/"}
    if root.tag != "{http://www.w3.org/2005/Atom}feed":
        raise ProviderError("arXiv response is not an Atom feed")
    total_text = root.findtext("open:totalResults", namespaces=ns)
    total = int(total_text) if total_text and total_text.isdigit() else None
    papers = []
    for entry in root.findall("atom:entry", ns):
        identity = entry.findtext("atom:id", "", ns)
        title = entry.findtext("atom:title", "", ns)
        if not title.strip():
            continue
        try:
            kind, identifier = normalize_identifier(identity)
        except ProviderError:
            continue
        if kind != "arxiv":
            continue
        published = entry.findtext("atom:published", "", ns)
        version_match = re.search(r"(v\d+)$", identifier)
        papers.append({"id": paper_id(kind, identifier), "identifiers": {kind: identifier},
                       "title": " ".join(title.split()),
                       "authors": [author.findtext("atom:name", "", ns) for author in entry.findall("atom:author", ns)],
                       "year": int(published[:4]) if published[:4].isdigit() else None,
                       "version": version_match.group(1) if version_match else "unknown",
                       "abstract": " ".join(entry.findtext("atom:summary", "", ns).split()),
                       "provider": "arxiv", "source_url": identity, "read_scope": "not_read"})
    return papers, total

def crossref_papers(body: bytes, *, resolve: bool = False) -> tuple[list[dict], int | None]:
    try:
        value = json.loads(body.decode("utf-8"))
        message = value["message"]
    except (ValueError, KeyError, UnicodeError, TypeError) as exc:
        raise ProviderError("malformed Crossref JSON response") from exc
    if not isinstance(message, dict):
        raise ProviderError("Crossref message must be an object")
    items = [message] if resolve else message.get("items", [])
    if not isinstance(items, list):
        raise ProviderError("Crossref items must be an array")
    papers = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            kind, identity = normalize_identifier(item.get("DOI", ""))
        except (ProviderError, AttributeError):
            continue
        titles = item.get("title", [])
        if kind != "doi" or not isinstance(titles, list) or not titles or not isinstance(titles[0], str) or not titles[0].strip():
            continue
        published = item.get("published")
        parts = published.get("date-parts", []) if isinstance(published, dict) else []
        year = parts[0][0] if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0] else None
        authors = item.get("author", [])
        if not isinstance(authors, list):
            authors = []
        papers.append({"id": paper_id(kind, identity), "identifiers": {kind: identity},
                       "title": titles[0], "authors": [" ".join(str(a.get(k, "")) for k in ("given", "family")).strip()
                                                       for a in authors if isinstance(a, dict)],
                       "year": year if type(year) is int and 1000 <= year <= 9999 else None,
                       "version": "unknown", "provider": "crossref",
                       "source_url": "https://doi.org/" + identity, "read_scope": "not_read"})
    total = message.get("total-results")
    return papers, total if type(total) is int and total >= 0 else None

def search_url(provider: str, query: str, limit: int) -> str:
    if provider == "arxiv":
        return "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"search_query": query,
             "start": 0, "max_results": limit, "sortBy": "relevance", "sortOrder": "descending"})
    if provider == "crossref":
        return "https://api.crossref.org/works?" + urllib.parse.urlencode({"query.bibliographic": query,
              "rows": limit, "sort": "score", "order": "desc"})
    raise ProviderError("provider must be arxiv or crossref")

def resolve_url(kind: str, identity: str) -> tuple[str, str]:
    if kind == "arxiv":
        return "arxiv", "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"id_list": identity})
    return "crossref", "https://api.crossref.org/works/" + urllib.parse.quote(identity, safe="")
