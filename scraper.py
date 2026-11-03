"""Scraper del catálogo de seminuevos/reacondicionados de Movistar y Entel Chile."""
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
    if next_link and next_link.get("href"):
        next_html = _fetch_movistar_html(next_link["href"])
        products.extend(_parse_movistar_products(next_html))

    return products


def get_movistar_products():
    html = _fetch_movistar_html()
    return _parse_movistar_products(html)


# ---------------------------------------------------------------------------
# Entel: catálogo Endeca/ACRS, con un bloque JSON embebido en el HTML.
# ---------------------------------------------------------------------------

ENTEL_BASE_URL = "https://miportal.entel.cl/personas/catalogo/seminuevos"
ENTEL_PAGE_SIZE = 24
ENTEL_MAX_PAGES = 10  # tope defensivo
ENTEL_RECORD_MARKER = '"@class": "com.endeca.infront.cartridge.model.Record"'

_ENTEL_FIELD_RES = {
    "name": re.compile(r'"displayName":\s*\["([^"]*)"\]'),
    "inventory": re.compile(r'"inventoryStatus":\s*\["([^"]*)"\]'),
    "price": re.compile(r'"productListPrice":\s*\["([\d.]+)"\]'),
    "url": re.compile(r'"seoUrl":\s*\["([^"]*)"\]'),
    "reference_price": re.compile(r'"referencePrice":\s*\["([\d.]+)"\]'),
}
_ENTEL_TOTAL_PAGES_RE = re.compile(r'"totalPagesNum":\s*(\d+)')


def _fetch_entel_html(offset=0, timeout=20):
    params = {
        "No": offset,
        "Nrpp": ENTEL_PAGE_SIZE,
        "contentPath": "/pages/storechilepp/catalogo/seminuevos",
        "eIdx": 5,
        "sIdx": 1,
        "subPath": "main[1]",
    }
    resp = requests.get(ENTEL_BASE_URL, params=params, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _parse_entel_products(html):
    products = []

    for chunk in html.split(ENTEL_RECORD_MARKER)[1:]:
        name_match = _ENTEL_FIELD_RES["name"].search(chunk)
        if not name_match:
            continue

        inventory_match = _ENTEL_FIELD_RES["inventory"].search(chunk)
        if not inventory_match or inventory_match.group(1) != "IN_STOCK":
            continue

        price_match = _ENTEL_FIELD_RES["price"].search(chunk)
        url_match = _ENTEL_FIELD_RES["url"].search(chunk)
        if not price_match or not url_match:
            continue

        name = name_match.group(1).strip()
        price = int(float(price_match.group(1)))
        url = "https://miportal.entel.cl" + url_match.group(1)

        product = {
            "name": name,
            "url": url,
            "price": price,
            "source": "Entel",
        }

        reference_match = _ENTEL_FIELD_RES["reference_price"].search(chunk)
        if reference_match:
            original_price = int(float(reference_match.group(1)))
            if original_price > price:
                pct = round(100 * (original_price - price) / original_price)
                product["discount_pct"] = f"-{pct}%"
                product["original_price"] = original_price

        products.append(product)

    return products


def get_entel_products():
    all_products = []
    offset = 0
    total_pages = 1

    for page in range(ENTEL_MAX_PAGES):
        html = _fetch_entel_html(offset)
        all_products.extend(_parse_entel_products(html))

        if page == 0:
            total_pages_match = _ENTEL_TOTAL_PAGES_RE.search(html)
            if total_pages_match:
                total_pages = int(total_pages_match.group(1))

        offset += ENTEL_PAGE_SIZE
        if page + 1 >= total_pages:
            break

    return all_products


# ---------------------------------------------------------------------------

SOURCES = {
    "Movistar": get_movistar_products,
    "Entel": get_entel_products,
}


def get_matching_products():
    matches = []
    for source_name, fetch_fn in SOURCES.items():
        try:
            products = fetch_fn()
        except Exception as exc:  # no dejar que una tienda caída tumbe la otra
            print(f"Error obteniendo catálogo de {source_name}: {exc}")
            continue

        matches.extend(
            p for p in products if is_desired_iphone(p["name"]) and p["price"] <= MAX_PRICE_CLP
        )

    return matches


if __name__ == "__main__":
    import json

    matches = get_matching_products()
    print(json.dumps(matches, indent=2, ensure_ascii=False))
    print(f"\n{len(matches)} producto(s) encontrados.")
