import asyncio
import csv
import json
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://iba-world.com"
START_URL = "https://iba-world.com/cocktails/all-cocktails/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL,
}

# Age gate için en pratik yöntem:
# Browser'daki "Remember me + Yes" davranışını taklit etmek.
COOKIES = {
    "age_gate_confirm": "1"
}

MAX_CONCURRENCY = 10
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3

sem = asyncio.Semaphore(MAX_CONCURRENCY)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_section_text_by_heading(soup: BeautifulSoup, heading_text: str) -> str:
    """
    <h4>Method</h4> gibi heading'i bulur, altındaki shortcode/container içindeki
    p/div metinlerini alır.
    """
    heading = soup.find(
        lambda tag: tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"]
        and clean_text(tag.get_text(" ", strip=True)).lower() == heading_text.lower()
    )
    if not heading:
        return ""

    parent_widget = heading.find_parent(class_=lambda c: c and "elementor-widget" in " ".join(c) if isinstance(c, list) else False)
    if parent_widget:
        next_widget = parent_widget.find_next_sibling(class_=lambda c: c and "elementor-widget" in " ".join(c) if isinstance(c, list) else False)
        if next_widget:
            text = clean_text(next_widget.get_text("\n", strip=True))
            return text

    # fallback
    nxt = heading.find_parent()
    if nxt:
        text = clean_text(nxt.get_text("\n", strip=True))
        if text.lower() != heading_text.lower():
            return text

    return ""


def extract_ingredients(soup: BeautifulSoup) -> list[str]:
    heading = soup.find(
        lambda tag: tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"]
        and clean_text(tag.get_text(" ", strip=True)).lower() == "ingredients"
    )
    if not heading:
        return []

    parent_widget = heading.find_parent(class_=lambda c: c and "elementor-widget" in " ".join(c) if isinstance(c, list) else False)
    if parent_widget:
        next_widget = parent_widget.find_next_sibling(class_=lambda c: c and "elementor-widget" in " ".join(c) if isinstance(c, list) else False)
        if next_widget:
            items = [clean_text(li.get_text(" ", strip=True)) for li in next_widget.select("li")]
            if items:
                return items
            raw = clean_text(next_widget.get_text("\n", strip=True))
            if raw:
                return [line.strip() for line in raw.split("\n") if line.strip()]

    return []


def extract_name(soup: BeautifulSoup) -> str:
    # Önce sayfa başlığını deneyelim
    for selector in ["h1", ".elementor-heading-title"]:
        el = soup.select_one(selector)
        if el:
            text = clean_text(el.get_text(" ", strip=True))
            if text and text.lower() not in {"ingredients", "method", "garnish"}:
                return text
    return ""


def extract_category_from_detail(soup: BeautifulSoup) -> str:
    text = soup.get_text("\n", strip=True)
    for category in ["The unforgettables", "Contemporary Classics", "New Era"]:
        if category.lower() in text.lower():
            return category
    return ""


async def fetch_text(client: httpx.AsyncClient, url: str) -> str:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with sem:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                await asyncio.sleep(1.5 * attempt)
    raise last_error


async def parse_listing_page(client: httpx.AsyncClient, url: str) -> list[dict]:
    html = await fetch_text(client, url)
    soup = BeautifulSoup(html, "html.parser")

    results = []
    seen = set()

    for card in soup.select(".cocktail"):
        a = card.select_one("a[href]")
        if not a:
            continue

        link = urljoin(BASE_URL, a["href"])
        if link in seen:
            continue
        seen.add(link)

        name = clean_text(card.select_one("h2").get_text(" ", strip=True)) if card.select_one("h2") else ""
        category_el = card.select_one(".cocktail-category")
        category = clean_text(category_el.get_text(" ", strip=True)) if category_el else ""
        views_el = card.select_one(".cocktail-views")
        views = clean_text(views_el.get_text(" ", strip=True)) if views_el else ""

        img_el = card.select_one("img")
        image_url = urljoin(BASE_URL, img_el["src"]) if img_el and img_el.get("src") else ""

        results.append({
            "name": name,
            "category": category,
            "views": views,
            "image_url": image_url,
            "url": link,
        })

    return results


async def discover_listing_pages(client):

    html = await fetch_text(client, START_URL)
    soup = BeautifulSoup(html, "html.parser")

    pages = [START_URL]

    numbers = []

    for el in soup.select(".page-numbers"):
        txt = el.text.strip()

        if txt.isdigit():
            numbers.append(int(txt))

    last_page = max(numbers)

    for i in range(2, last_page + 1):
        pages.append(f"{START_URL}page/{i}/")

    return pages


async def scrape_cocktail_detail(client: httpx.AsyncClient, item: dict) -> dict:
    html = await fetch_text(client, item["url"])
    soup = BeautifulSoup(html, "html.parser")

    name = extract_name(soup) or item.get("name", "")
    ingredients = extract_ingredients(soup)
    method = extract_section_text_by_heading(soup, "Method")
    garnish = extract_section_text_by_heading(soup, "Garnish")
    category = item.get("category", "") or extract_category_from_detail(soup)

    return {
        "name": name,
        "category": category,
        "views": item.get("views", ""),
        "ingredients": ingredients,
        "method": method,
        "garnish": garnish,
        "image_url": item.get("image_url", ""),
        "url": item["url"],
    }


def save_json(data: list[dict], path: str = "cocktails.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_csv(data: list[dict], path: str = "cocktails.csv") -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "name",
                "category",
                "views",
                "ingredients",
                "method",
                "garnish",
                "image_url",
                "url",
            ],
        )
        writer.writeheader()
        for row in data:
            row = row.copy()
            row["ingredients"] = " | ".join(row.get("ingredients", []))
            writer.writerow(row)


async def main():
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)

    async with httpx.AsyncClient(
    headers=HEADERS,
    cookies=COOKIES,
    timeout=REQUEST_TIMEOUT,
    limits=limits,
    verify=False
) as client:

        print("Liste sayfaları keşfediliyor...")
        listing_pages = await discover_listing_pages(client)
        print(f"{len(listing_pages)} adet liste sayfası bulundu.")

        listing_tasks = [parse_listing_page(client, page_url) for page_url in listing_pages]
        listing_results = await asyncio.gather(*listing_tasks)

        raw_items = []
        seen_urls = set()
        for page_items in listing_results:
            for item in page_items:
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    raw_items.append(item)

        print(f"{len(raw_items)} adet kokteyl linki bulundu.")

        detail_tasks = [scrape_cocktail_detail(client, item) for item in raw_items]
        cocktails = await asyncio.gather(*detail_tasks)

        cocktails = sorted(cocktails, key=lambda x: x["name"].lower())

        save_json(cocktails, "cocktails.json")
        save_csv(cocktails, "cocktails.csv")

        print(f"Tamamlandı. {len(cocktails)} kayıt yazıldı.")
        print("Dosyalar: cocktails.json, cocktails.csv")


if __name__ == "__main__":
    asyncio.run(main())