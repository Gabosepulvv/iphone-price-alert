"""Scraper del catálogo de seminuevos/reacondicionados de Movistar Chile."""
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CL,es;q=0.9",
}

# Modelos de interés: iPhone 14, 15 o 16 (incluye Pro, Pro Max, Plus), excluyendo 16e.
MODEL_RE = re.compile(r"iPhone\s+(14|15|16)(e)?\b", re.IGNORECASE)
STORAGE_RE = re.compile(r"(\d{2,4})\s*GB", re.IGNORECASE)
PRICE_RE = re.compile(r"[\d.]+")

MIN_STORAGE_GB = 128
MAX_PRICE_CLP = 700_000


def is_desired_iphone(name):
    match = MODEL_RE.search(name)
    if not match:
        return False
    if match.group(2):  # evita "16e"
        return False

    storage_match = STORAGE_RE.search(name)
    if not storage_match:
        return False

    storage_gb = int(storage_match.group(1))
    return storage_gb >= MIN_STORAGE_GB


def _parse_clp(text):
    if not text:
        return None
    match = PRICE_RE.search(text)
    if not match:
        return None
    digits = match.group(0).replace(".", "")
    return int(digits) if digits else None


# ---------------------------------------------------------------------------
# Movistar: catálogo Magento, HTML server-rendered.
# ---------------------------------------------------------------------------

MOVISTAR_CATALOG_URL = "https://catalogo.movistar.cl/tienda/outlet/celulares-reacondicionados"


def _fetch_movistar_html(url=MOVISTAR_CATALOG_URL, timeout=20):
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _parse_movistar_products(html):
    soup = BeautifulSoup(html, "lxml")
    products = []

    for li in soup.select("li.item.product.product-item"):
        link_tag = li.select_one("a.product-item-photo")
        name_tag = li.select_one("a.product-item-link")
        price_tag = li.select_one(".divCon-plan-txt-valor-sinLabel")
        discount_tag = li.select_one(".divSin-plan-txt-dcto")
        old_price_tag = li.select_one(".old-price .price")

        if not link_tag or not name_tag or not price_tag:
            continue

        name = name_tag.get_text(strip=True)
        url = link_tag.get("href", "").strip()
        price = _parse_clp(price_tag.get_text(strip=True))
        if not name or not url or price is None:
            continue

        product = {
            "name": name,
            "url": url,
            "price": price,
            "source": "Movistar",
        }

        if discount_tag:
            discount_text = discount_tag.get_text(strip=True)
            if discount_text:
                product["discount_pct"] = discount_text
        if old_price_tag:
            old_price = _parse_clp(old_price_tag.get_text(strip=True))
            if old_price:
                product["original_price"] = old_price

        products.append(product)

    # Soporte defensivo por si el catálogo llega a paginar en el futuro.
    next_link = soup.select_one("a.action.next")
    next_href = next_link.get("href") if next_link else None
    if next_href and next_href.startswith("http"):
        next_html = _fetch_movistar_html(next_href)
        products.extend(_parse_movistar_products(next_html))

    return products


def get_movistar_products():
    html = _fetch_movistar_html()
    return _parse_movistar_products(html)


def get_matching_products():
    products = get_movistar_products()
    return [
        p
        for p in products
        if is_desired_iphone(p["name"]) and p["price"] <= MAX_PRICE_CLP
    ]


if __name__ == "__main__":
    import json

    matches = get_matching_products()
    print(json.dumps(matches, indent=2, ensure_ascii=False))
    print(f"\n{len(matches)} producto(s) encontrados.")
