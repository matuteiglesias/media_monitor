import argparse
import os
from datetime import datetime, timedelta
import feedparser
import csv
import pandas as pd

# ======================= CONFIG =======================
RSS_FEEDS = {
    "Inflación y Precios": "https://news.google.com/rss/search?q=(%22inflación%22+OR+%22IPC%22+OR+%22canasta+básica%22+OR+INDEC+OR+consultoras)+Argentina&hl=es-419&gl=AR&ceid=AR:es-419",
    "Tipo de Cambio y Reservas": "https://news.google.com/rss/search?q=dólar+OR+blue+OR+oficial+OR+reservas+OR+BCRA+OR+intervención+OR+futuros+OR+planchado&hl=es-419&gl=AR&ceid=AR:es-419",
    "Deuda y Financiamiento": "https://news.google.com/rss/search?q=bono+OR+licitación+OR+vencimientos+OR+Bonte+OR+tasa+OR+rollover&hl=es-419&gl=AR&ceid=AR:es-419",
    "Actividad y Empleo": "https://news.google.com/rss/search?q=subsidios+OR+paritarias+OR+gremios+OR+conciliación+OR+emple+OR+trabaj+OR+informal+OR+desemple+OR+EPH+OR+salarios&hl=es-419&gl=AR&ceid=AR:es-419",
    "Sector Externo": "https://news.google.com/rss/search?q=(comerc+exterior+OR+balanz+argentin+OR+export+OR+import+OR+arancel)+site:infobae.com+OR+site:lanacion.com.ar+OR+site:clarin.com+OR+site:ambito.com.ar+OR+site:telam.com.ar+OR+site:iprofesional.com&hl=es-419&gl=AR&ceid=AR:es-419",
    "Finanzas": "https://news.google.com/rss/search?q=(gasto+public+OR+ajuste+fiscal+OR+deficit+OR+superavit+OR+BCRA+OR+presupuesto+OR+bono+OR+banco+OR+riesgo+pais+OR+tasa+interes+OR+financier)&site:ambito.com.ar+OR+site:infobae.com+OR+site:lanacion.com.ar+OR+site:cronista.com+OR+site:baenegocios.com+OR+site:bna.com.ar&hl=es-419&gl=AR&ceid=AR:es-419",
    "Personajes Políticos y Económicos": "https://news.google.com/rss/search?q=(Milei+OR+Caputo+OR+Bausili+OR+Rubinstein+OR+Prat-Gay+OR+Cavallo+OR+Cristina+OR+Massa+OR+Melconian+OR+Macri+OR+Kicillof)+site:.ar&hl=es-419&gl=AR&ceid=AR:es-419",

}

DUMP_PATH = "./data/rss_slices/rss_dumps.csv"
SLICE_DIR = "./data/rss_slices/"
MAX_ARTICLES = 100
os.makedirs(SLICE_DIR, exist_ok=True)

# ======================= UTILITIES =======================
def clean_title(title):
    return title.rsplit(" - ", 1)[0].strip()

def fetch_and_save_news(rss_dict, output_csv, max_articles=100):
    rows = []
    for topic, url in rss_dict.items():
        feed = feedparser.parse(url)
        entries = feed.entries[:max_articles]
        for entry in entries:
            title = clean_title(entry.title)
            link = entry.link
            published = entry.get("published", "")
            source = entry.source.title if hasattr(entry, "source") else "N/A"
            source_url = entry.source.href if hasattr(entry, "source") else "N/A"

            rows.append([topic, title, link, published, source, source_url])
            # rows.append([topic, title, published, source])
    
    # 💾 Escribir a CSV
    with open(output_csv, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Topic", "Title", "Link", "Published", "Source", "Source URL"])
        # writer.writerow(["Topic", "Title", "Published", "Source"])
        writer.writerows(rows)
    
    print(f"\n✅ Guardado: {output_csv} con {len(rows)} artículos.")

def load_rss_dataset(csv_path):
    df = pd.read_csv(csv_path)
    df["Published"] = pd.to_datetime(df["Published"], errors="coerce", utc=True)
    df = df.dropna(subset=["Published"])
    return df

def compute_slices(trigger_time: datetime):
    slices = []

    def add_slice(label, start_delta, end_delta):
        start = trigger_time - timedelta(hours=end_delta)
        end = trigger_time - timedelta(hours=start_delta)
        slices.append({"label": label, "start": start, "end": end})

    h = trigger_time.hour
    d = trigger_time.day

    if h % 4 == 0:
        add_slice("4h_window", 2, 8)
    if h % 8 == 0:
        add_slice("8h_window", 4, 16)
    if h == 12:
        add_slice("2day_window", 12, 60)
        if d % 3 == 0:
            add_slice("3day_window", 72, 168)
        if d % 7 == 0:
            add_slice("weekly_window", 168, 336)
        if d % 14 == 0:
            add_slice("fortnight_window", 360, 1080)
    return slices

def apply_slices(df_news, slices, trigger_time):
    saved_files = []
    for s in slices:
        label = s["label"]
        start = pd.to_datetime(s["start"]).tz_convert("UTC")
        end = pd.to_datetime(s["end"]).tz_convert("UTC")
        sliced_df = df_news[(df_news["Published"] >= start) & (df_news["Published"] <= end)]
        if not sliced_df.empty:
            filename = f"{label}_{trigger_time.strftime('%Y%m%dT%H%M')}.csv"
            filepath = os.path.join(SLICE_DIR, filename)
            sliced_df.to_csv(filepath, index=False)
            saved_files.append(filepath)
    return saved_files

# ======================= MAIN =======================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trigger-time", type=str, default=None,
                        help="Timestamp in ISO format (e.g., 2025-05-28T12:00). If not set, uses current UTC time.")
    args = parser.parse_args()

    if args.trigger_time:
        trigger_time = datetime.fromisoformat(args.trigger_time).astimezone(tz=datetime.timezone.utc)
    else:
        trigger_time = datetime.utcnow()

    fetch_and_save_news(RSS_FEEDS, DUMP_PATH, MAX_ARTICLES)
    df_news = load_rss_dataset(DUMP_PATH)
    slices = compute_slices(trigger_time)
    saved = apply_slices(df_news, slices, trigger_time)

    print(f"✅ {len(saved)} archivos guardados: ")
    for s in saved:
        print(" -", s)
