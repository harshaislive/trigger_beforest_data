from __future__ import annotations

import hashlib
import json
import re
import sys
import argparse
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.crewai_manychat.convex_client import get_convex_client

SEED_DOMAINS = [
    "beforest.co",
    "bewild.life",
    "hospitality.beforest.co",
    "experiences.beforest.co",
    "10percent.beforest.co",
]

BRAND_BY_DOMAIN = {
    "beforest.co": "beforest",
    "bewild.life": "bewild",
    "hospitality.beforest.co": "hospitality",
    "experiences.beforest.co": "experiences",
    "10percent.beforest.co": "10percent",
}


@dataclass
class UrlEntry:
    url: str
    lastmod: str | None = None
    source: str | None = None


class HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        return " ".join(self._chunks)


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.add(value.strip())


def get(url: str, timeout: int = 25) -> requests.Response:
    headers = {
        "User-Agent": "beforest-crawler/1.0 (+https://beforest.co)",
        "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8",
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def strip_ns(tag: str) -> str:
    return tag.split("}")[-1].lower()


def discover_from_sitemap(sitemap_url: str, seen_sitemaps: set[str], out_urls: list[UrlEntry]) -> None:
    if sitemap_url in seen_sitemaps:
        return
    seen_sitemaps.add(sitemap_url)

    response = get(sitemap_url)
    root = ET.fromstring(response.text)

    children = list(root)
    if not children:
        return

    root_tag = strip_ns(root.tag)
    if root_tag == "sitemapindex":
        for child in children:
            if strip_ns(child.tag) != "sitemap":
                continue
            loc = None
            for node in child:
                if strip_ns(node.tag) == "loc" and node.text:
                    loc = node.text.strip()
            if loc:
                discover_from_sitemap(loc, seen_sitemaps, out_urls)
        return

    if root_tag == "urlset":
        for child in children:
            if strip_ns(child.tag) != "url":
                continue
            loc = None
            lastmod = None
            for node in child:
                tag = strip_ns(node.tag)
                if tag == "loc" and node.text:
                    loc = node.text.strip()
                elif tag == "lastmod" and node.text:
                    lastmod = node.text.strip()
            if loc:
                out_urls.append(UrlEntry(url=loc, lastmod=lastmod, source=sitemap_url))


def discover_domain_urls(domain: str) -> list[UrlEntry]:
    sitemap_candidates = [
        f"https://{domain}/sitemap.xml",
        f"https://{domain}/sitemap_index.xml",
    ]
    seen_sitemaps: set[str] = set()
    urls: list[UrlEntry] = []

    for sitemap_url in sitemap_candidates:
        try:
            discover_from_sitemap(sitemap_url, seen_sitemaps, urls)
        except Exception:
            continue

    if not urls:
        fallback = discover_from_homepage(domain, max_pages=80)
        urls.extend(fallback)

    unique: dict[str, UrlEntry] = {}
    for row in urls:
        parsed = urlparse(row.url)
        if parsed.scheme not in {"http", "https"}:
            continue
        unique[row.url] = row
    return list(unique.values())


def discover_from_homepage(domain: str, max_pages: int = 80) -> list[UrlEntry]:
    base = f"https://{domain}"
    queue = [base + "/"]
    seen: set[str] = set()
    out: list[UrlEntry] = []

    while queue and len(out) < max_pages:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)

        try:
            response = get(current)
        except Exception:
            continue

        out.append(UrlEntry(url=current, source="homepage-crawl"))

        extractor = LinkExtractor()
        extractor.feed(response.text)
        for href in extractor.links:
            if not href or href.startswith("#"):
                continue
            if href.startswith("http://") or href.startswith("https://"):
                parsed = urlparse(href)
                if parsed.netloc != domain:
                    continue
                target = href
            else:
                if href.startswith("/"):
                    target = base + href
                else:
                    target = base + "/" + href

            target = target.split("#", 1)[0]
            if target not in seen and target not in queue and len(queue) + len(out) < max_pages * 3:
                queue.append(target)

    return out


def extract_title(html: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return unescape(" ".join(match.group(1).split())).strip()[:240]


def extract_ld_json_objects(html: str) -> Iterable[dict]:
    for match in re.finditer(
        r"<script[^>]*type=['\"]application/ld\+json['\"][^>]*>(.*?)</script>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        raw = match.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if isinstance(data, dict):
            yield data
        elif isinstance(data, list):
            for obj in data:
                if isinstance(obj, dict):
                    yield obj


def classify_page(url: str) -> str:
    path = urlparse(url).path.lower()
    if "/products/" in path:
        return "product"
    if "/collections/" in path:
        return "collection"
    if "/blogs/" in path:
        return "blog"
    return "page"


def crawl_entry(client, domain: str, entry: UrlEntry) -> tuple[bool, bool]:
    url = entry.url
    page_type = classify_page(url)
    try:
        response = get(url)
        html = response.text
        title = extract_title(html)

        extractor = HtmlTextExtractor()
        extractor.feed(html)
        text = " ".join(extractor.text().split())
        if len(text) > 12000:
            text = text[:12000]

        content_hash = hash_text(text)

        client.upsert_crawl_url(
            domain=domain,
            url=url,
            status="ok",
            page_type=page_type,
            source=entry.source,
            lastmod=entry.lastmod,
            content_hash=content_hash,
            title=title,
        )

        if text:
            client.upsert_knowledge_item(
                url=url,
                title=title,
                content=text,
                summary=text[:350],
            )

        product_saved = False
        if domain == "bewild.life" and page_type == "product":
            product_name = title or ""
            price_text = None
            availability = None

            for obj in extract_ld_json_objects(html):
                if obj.get("@type") == "Product":
                    if obj.get("name"):
                        product_name = str(obj.get("name"))
                    offers = obj.get("offers")
                    if isinstance(offers, dict):
                        price_text = str(offers.get("price") or "") or price_text
                        availability = str(offers.get("availability") or "") or availability
                    break

            if not product_name:
                path_part = urlparse(url).path.rsplit("/", 1)[-1].replace("-", " ").strip()
                product_name = path_part.title() or "Unknown Product"

            collection_match = re.search(r"/collections/([^/]+)", urlparse(url).path)
            category = collection_match.group(1).replace("-", " ") if collection_match else "shop"

            client.upsert_product(
                brand="bewild",
                domain=domain,
                name=product_name,
                url=url,
                category=category,
                availability=availability,
                price_text=price_text,
                source=entry.source,
                content_hash=content_hash,
            )
            product_saved = True

        return True, product_saved
    except Exception as exc:
        client.upsert_crawl_url(
            domain=domain,
            url=url,
            status="error",
            page_type=page_type,
            source=entry.source,
            lastmod=entry.lastmod,
            error=str(exc)[:400],
        )
        return False, False


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl sitemap URLs and sync to Convex")
    parser.add_argument(
        "--domains",
        type=str,
        default=",".join(SEED_DOMAINS),
        help="Comma-separated domains to crawl",
    )
    parser.add_argument(
        "--max-urls-per-domain",
        type=int,
        default=0,
        help="Optional cap per domain (0 means no cap)",
    )
    args = parser.parse_args()

    target_domains = [d.strip() for d in args.domains.split(",") if d.strip()]

    client = get_convex_client()
    total_urls = 0
    ok_urls = 0
    skipped_urls = 0
    product_rows = 0

    for domain in target_domains:
        urls = discover_domain_urls(domain)
        if args.max_urls_per_domain > 0:
            urls = urls[: args.max_urls_per_domain]
        print(f"{domain}: discovered {len(urls)} urls from sitemap")
        total_urls += len(urls)

        for entry in urls:
            existing = client.get_crawl_url_by_url(entry.url)
            if (
                existing
                and existing.get("status") == "ok"
                and entry.lastmod
                and existing.get("lastmod") == entry.lastmod
            ):
                skipped_urls += 1
                continue

            ok, product_saved = crawl_entry(client, domain, entry)
            if ok:
                ok_urls += 1
            if product_saved:
                product_rows += 1

    print(
        f"Done. Crawled {ok_urls}/{total_urls} urls successfully. "
        f"Skipped unchanged: {skipped_urls}. "
        f"Product rows upserted: {product_rows}."
    )


if __name__ == "__main__":
    main()
