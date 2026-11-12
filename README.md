# Alerta de precios iPhone reacondicionado (Movistar Chile)

Revisa 2 veces al día el catálogo de seminuevos de
[Movistar](https://catalogo.movistar.cl/tienda/outlet/celulares-reacondicionados)
buscando iPhone 14, 15 o 16 (normal, Plus, Pro o Pro Max) con 128GB o más y
precio máximo de **$700.000 CLP** (cualquier modelo que supere ese tope se
ignora por completo), y avisa por Telegram cuando:

- **Aparece un modelo nuevo** que antes no estaba en el catálogo.
- **Baja a su precio mínimo histórico** (nunca estuvo más barato desde que el bot lo sigue).
- **Tiene un descuento activo** (precio tachado / "-XX%" en el catálogo).

No hace falta definir un precio tope manualmente: el bot guarda el historial de
precios de cada producto (`history.json`) y detecta solo cuándo algo está
"más barato de lo normal".

## 1. Crear el bot de Telegram

Como ya tienes un bot usado para otra cosa, hay que crear uno **nuevo y
separado**:

1. Abre Telegram y busca **@BotFather**.
2. Envía `/newbot`.
3. Dale un nombre y un username (debe terminar en `bot`, ej: `MisIphonesAlertBot`).
4. BotFather te entrega un **token** (algo como `123456789:ABCdefGhIJKlmNoPQRstuVWxyz`). Guárdalo.
5. Abre una conversación con tu bot nuevo (búscalo por su username) y envíale cualquier mensaje, ej. `hola` (si no le escribes primero, el bot no puede enviarte mensajes a ti).
6. Obtén tu **chat_id**: abre en el navegador, reemplazando `<TOKEN>`:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   Busca en la respuesta JSON el campo `"chat":{"id": ...}` — ese número es tu `chat_id`.

## 2. Probar localmente (opcional pero recomendado)

```bash
cd iphone-price-alert
pip install -r requirements.txt
python main.py --dry-run
```

Esto imprime en consola lo que encontró y el mensaje que enviaría, sin tocar
Telegram ni guardar el historial. Si se ve bien, corre sin `--dry-run` una vez
(con las variables de entorno `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`
seteadas) para probar el envío real.

## 3. Subir a GitHub

```bash
git init
git add .
git commit -m "Bot de alertas de precio iPhone reacondicionado"
gh repo create iphone-price-alert --private --source=. --remote=origin --push
```

(Si no tienes `gh` instalado, crea el repo manualmente en github.com y luego
`git remote add origin <url>` + `git push -u origin main`.)

## 4. Configurar los secrets en GitHub

En el repo: **Settings → Secrets and variables → Actions → New repository secret**

- `TELEGRAM_BOT_TOKEN`: el token de BotFather.
- `TELEGRAM_CHAT_ID`: el chat_id obtenido antes.

## 5. Listo

El workflow en `.github/workflows/check-prices.yml` corre automáticamente
2 veces al día (13:00 y 23:00 UTC ≈ 10:00/20:00 hora de Chile en horario de
verano). También puedes dispararlo manualmente desde la pestaña
**Actions → check-prices → Run workflow** para probarlo sin esperar.

## 6. Reporte visual (GitHub Pages)

Cada corrida también genera `docs/index.html` con el historial de precios
y un gráfico por producto, publicado automáticamente en:

**https://gabosepulvv.github.io/iphone-price-alert/**

El repo es público para que esta página funcione gratis (GitHub Pages en
repos privados requiere un plan de pago). Solo se expone el código y los
precios públicos de Movistar — el token de Telegram y el chat_id siguen
siendo secrets privados, nunca quedan en el repo.

### Primera corrida

En la primera ejecución, **todo** lo que haya en el catálogo que cumpla los
criterios se reportará como "nuevo ingreso" (porque el historial está vacío).
Es esperado — es tu punto de partida. De ahí en adelante solo avisa sobre
cambios reales.

### Ajustar criterios

- Modelos, GB mínimos y precio tope: `scraper.py`, variables `MODEL_RE`,
  `MIN_STORAGE_GB` y `MAX_PRICE_CLP`.
- Frecuencia de revisión: `.github/workflows/check-prices.yml`, línea `cron`.

