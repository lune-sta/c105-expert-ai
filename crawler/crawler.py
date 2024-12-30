import os
import urllib.parse
from pathlib import Path
import time
import multiprocessing
from functools import partial
from typing import Optional, TypedDict, List
import json

from playwright.sync_api import sync_playwright
import trafilatura
from bs4 import BeautifulSoup

from models import Page

# ファイル保存先
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"
INTERVAL = 0.1


class CrawlProps(TypedDict, total=False):
    host: str
    path_prefix: str
    start_url: str
    suffixes: Optional[List[str]]
    ignore_suffixes: Optional[List[str]]
    languages: List[str]
    projects: List[str]


def start_crawl(props: CrawlProps):
    initial_page = Page()
    initial_page.host = props.get("host")
    initial_page.url = props.get("start_url")
    initial_page.save()

    with multiprocessing.Pool() as pool:
        scrape_func = partial(_scrape_page, props)

        while True:
            pages = Page.select().where(
                Page.host == props.get("host"), Page.is_scraped == False
            )
            print(f"Remaining {str(len(pages))} pages")
            if not pages:
                return

            pool.map(scrape_func, pages)
            time.sleep(INTERVAL)


def _scrape_page(props: CrawlProps, page: Page):
    try:
        print(page.url)
        parsed_url = urllib.parse.urlparse(page.url)

        file_path = OUTPUT_DIR / parsed_url.netloc / parsed_url.path.lstrip("/")
        if not file_path.suffix:
            file_path = file_path / "index.md"
        else:
            file_path = file_path.with_suffix(".md")

        if os.path.exists(file_path):
            exit()

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            browser_page = context.new_page()

            browser_page.goto(page.url, wait_until="networkidle")
            content = browser_page.content()

            # HTMLコンテンツからMarkdownを抽出
            result = trafilatura.extract(content, output_format="markdown")

            os.makedirs(file_path.parent, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(result)

            _save_metadata(
                file_path,
                page.url,
                browser_page.title(),
                props.get("languages", []),
                props.get("projects", []),
            )
            _discover_and_save_links(props, parsed_url.path, content.encode())

            browser.close()

        page.is_scraped = True
        page.save()
    except TypeError:
        pass
    except Exception as e:
        print(f"Error scraping {page.url}: {e}")


# 毎回DBにgetしてると遅すぎて発狂しそうだったのでキャッシュを持つ
_discovered = {}


def _save_metadata(
    file_path: Path, url: str, title: str, languages: list[str], projects: list[str]
):
    metadata = {
        "metadataAttributes": {
            "languages": languages,
            "projects": projects,
            "url": url,
            #"title": title,
        }
    }
    metadata_path = file_path.with_suffix(".md.metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)


def _discover_and_save_links(props: CrawlProps, path: str, content: bytes):
    soup = BeautifulSoup(content, "lxml")
    for a in soup.findAll("a"):
        link = a.get("href")

        if not link or ":" in link or link.startswith("#"):
            continue

        if "#" in link:
            link = link.split("#")[0]

        if link.startswith("/"):
            new_path = link
        else:
            if path.endswith("/"):
                new_path = path + link
            else:
                new_path = os.path.dirname(path) + "/" + link

        new_path = os.path.normpath(new_path)

        if not new_path.startswith(props.get("path_prefix", "")):
            continue

        suffixes = props.get("suffixes")
        if suffixes:
            if not any(new_path.endswith(suffix) for suffix in suffixes):
                continue

        ignore_suffixes = props.get("ignore_suffixes")
        if ignore_suffixes:
            if any(new_path.endswith(suffix) for suffix in ignore_suffixes):
                continue

        url = props.get("host", "") + new_path
        if url in _discovered:
            continue

        if not Page.get_or_none(Page.url == url):
            page = Page()
            page.host = props.get("host", "")
            page.url = url
            page.save()

        _discovered[url] = True
