"""Orquesta: scrapea Movistar, compara contra el historial y avisa por Telegram."""
import json
import os
import sys
from datetime import datetime, timezone

from scraper import get_matching_products
from notifier import send_telegram_message

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "history.json")
MAX_HISTORY_POINTS = 60


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return {}
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def format_clp(amount):
    return f"${amount:,.0f}".replace(",", ".")


def evaluate(products, history, now_iso):
    """Compara los productos actuales contra el historial y arma las alertas."""
    alerts = []

    for product in products:
        url = product["url"]
        price = product["price"]
        entry = history.get(url)

        if entry is None:
            history[url] = {
                "name": product["name"],
                "first_seen": now_iso,
                "last_seen": now_iso,
                "min_price": price,
                "last_price": price,
                "history": [{"date": now_iso, "price": price}],
            }
            alerts.append((product, "nuevo_ingreso"))
            continue

        is_new_low = price < entry["min_price"]
        has_discount = bool(product.get("discount_pct"))

        entry["name"] = product["name"]
        entry["last_seen"] = now_iso
        entry["last_price"] = price
        entry["history"].append({"date": now_iso, "price": price})
        entry["history"] = entry["history"][-MAX_HISTORY_POINTS:]

        if is_new_low:
            entry["min_price"] = price
            alerts.append((product, "nuevo_minimo"))
        elif has_discount:
            alerts.append((product, "oferta"))

    return alerts


REASON_LABELS = {
    "nuevo_ingreso": "Nuevo ingreso al catálogo",
    "nuevo_minimo": "Nuevo precio mínimo histórico",
    "oferta": "En oferta",
}


def build_message(alerts):
    lines = ["<b>📱 Alerta iPhone reacondicionado</b>", ""]
    for product, reason in alerts:
        lines.append(f"<b>[{product.get('source', '?')}] {product['name']}</b>")
        lines.append(f"Motivo: {REASON_LABELS[reason]}")
        price_line = f"Precio: {format_clp(product['price'])}"
        if product.get("original_price"):
            price_line += f" (antes {format_clp(product['original_price'])}, {product.get('discount_pct', '')})"
        lines.append(price_line)
        lines.append(product["url"])
        lines.append("")
    return "\n".join(lines).strip()


def main():
    dry_run = "--dry-run" in sys.argv
    now_iso = datetime.now(timezone.utc).isoformat()

    products = get_matching_products()
    history = load_history()
    alerts = evaluate(products, history, now_iso)

    print(f"Productos encontrados: {len(products)}")
    print(f"Alertas generadas: {len(alerts)}")

    if alerts:
        message = build_message(alerts)
        print("\n--- Mensaje ---\n" + message)

        if not dry_run:
            token = os.environ["TELEGRAM_BOT_TOKEN"]
            chat_id = os.environ["TELEGRAM_CHAT_ID"]
            send_telegram_message(token, chat_id, message)
            print("\nMensaje enviado a Telegram.")
        else:
            print("\n(dry-run: no se envió nada a Telegram)")
    else:
        print("Sin novedades en esta corrida.")

    if not dry_run:
        save_history(history)


if __name__ == "__main__":
    main()
