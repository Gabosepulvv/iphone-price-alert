"""Genera docs/index.html: una página estática con el historial de precios."""
import html
import json
import os
from datetime import datetime, timezone

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "history.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "docs", "index.html")


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return {}
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def format_clp(amount):
    return f"${amount:,.0f}".replace(",", ".")


def build_html(history):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    products = sorted(history.items(), key=lambda kv: kv[1]["last_seen"], reverse=True)

    cards = []
    chart_data = {}

    for idx, (url, entry) in enumerate(products):
        canvas_id = f"chart-{idx}"
        chart_data[canvas_id] = {
            "labels": [point["date"][:10] for point in entry["history"]],
            "prices": [point["price"] for point in entry["history"]],
        }

        name = html.escape(entry["name"])
        safe_url = html.escape(url, quote=True)
        cards.append(f"""
        <div class="card">
          <h2><a href="{safe_url}" target="_blank" rel="noopener">{name}</a></h2>
          <p class="price">Precio actual: <strong>{format_clp(entry['last_price'])}</strong>
             &middot; Mínimo histórico: {format_clp(entry['min_price'])}</p>
          <p class="meta">Visto por primera vez: {entry['first_seen'][:10]}
             &middot; Última vez: {entry['last_seen'][:10]}</p>
          <canvas id="{canvas_id}" height="80"></canvas>
        </div>""")

    cards_html = "\n".join(cards) if cards else "<p>Todavía no hay productos en el historial.</p>"

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Historial de precios · iPhone reacondicionado</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 16px; }}
  .card {{ border: 1px solid #8884; border-radius: 12px; padding: 16px; margin-bottom: 20px; }}
  h2 {{ font-size: 18px; margin: 0 0 8px; }}
  h2 a {{ color: inherit; text-decoration: none; }}
  h2 a:hover {{ text-decoration: underline; }}
  .price {{ margin: 4px 0; }}
  .meta {{ color: #888; font-size: 13px; margin: 0 0 12px; }}
  header {{ margin-bottom: 24px; }}
  footer {{ color: #888; font-size: 12px; text-align: center; margin-top: 24px; }}
</style>
</head>
<body>
<header>
  <h1>📱 Historial de precios · iPhone reacondicionado (Movistar)</h1>
  <p>Última actualización: {now}</p>
</header>
<main>
{cards_html}
</main>
<footer>Generado automáticamente desde history.json en cada corrida del bot.</footer>
<script>
const chartData = {json.dumps(chart_data, ensure_ascii=False)};
for (const [id, data] of Object.entries(chartData)) {{
  new Chart(document.getElementById(id), {{
    type: 'line',
    data: {{
      labels: data.labels,
      datasets: [{{
        label: 'Precio (CLP)',
        data: data.prices,
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37,99,235,0.1)',
        tension: 0.2,
        fill: true,
      }}]
    }},
    options: {{
      plugins: {{ legend: {{ display: false }} }},
      scales: {{ y: {{ ticks: {{ callback: (v) => '$' + v.toLocaleString('es-CL') }} }} }}
    }}
  }});
}}
</script>
</body>
</html>
"""


def main():
    history = load_history()
    output_html = build_html(history)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(output_html)
    print(f"Reporte generado en {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
