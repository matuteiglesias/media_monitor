import argparse
import os
from datetime import datetime, timedelta, timezone
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

DUMP_PATH = "./data/rss_slices/rss_dumps"
SLICE_DIR = "./data/rss_slices/"
MAX_ARTICLES = 100
os.makedirs(SLICE_DIR, exist_ok=True)

# ======================= UTILITIES =======================
def clean_title(title):
    return title.rsplit(" - ", 1)[0].strip()

import hashlib

def compute_uid(title, source):
    raw = f"{title}_{source}"
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()[:10]  # hash corto



def fetch_and_save_news(rss_dict, output_csv, max_articles=100, digest_id=None):
    articles = []
    seen_uids = set()

    for topic, url in rss_dict.items():
        feed = feedparser.parse(url)
        entries = feed.entries[:max_articles]
        for entry in entries:
            title = clean_title(entry.title)
            link = entry.link
            published = entry.get("published", "")
            source = entry.source.title if hasattr(entry, "source") else "N/A"
            source_url = entry.source.href if hasattr(entry, "source") else "N/A"
            uid = compute_uid(title, source)

            if uid in seen_uids:
                continue  # Skip duplicates
            seen_uids.add(uid)

            articles.append({
                "digest_id": digest_id,
                "uid": uid,
                "Topic": topic,
                "Title": title,
                "Link": link,
                "Published": published,
                "Source": source,
                "Source URL": source_url,
            })

    # Convert to DataFrame
    df = pd.DataFrame(articles)

    # Robust date parsing
    df["Published"] = pd.to_datetime(df["Published"], errors="coerce", utc=True)
    df = df.dropna(subset=["Published"])  # Drop entries with invalid date
    df = df.sort_values("Published").reset_index(drop=True)

    # Assign article_id sequentially
    df.insert(0, "article_id", df.index + 1)

    # Save to CSV
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"\n✅ Saved: {output_csv} with {len(df)} unique and sorted articles.")


def load_rss_dataset(csv_path):
    df = pd.read_csv(csv_path)
    df["Published"] = pd.to_datetime(df["Published"], errors="coerce", utc=True)
    df = df.dropna(subset=["Published"])
    df = df.sort_values("Published")
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
        
    print(slices)
    return slices



def apply_slices(df_news, slices, trigger_time):
    saved_files = []
    df_news["Published"] = pd.to_datetime(df_news["Published"], utc=True)
    
    for s in slices:
        label = s["label"]
        
        start = pd.to_datetime(s["start"])
        if start.tzinfo is None:
            start = start.tz_localize("UTC")
        else:
            start = start.tz_convert("UTC")        

        end = pd.to_datetime(s["end"])
        if end.tzinfo is None:
            end = end.tz_localize("UTC")
        else:
            end = end.tz_convert("UTC")


        sliced_df = df_news[(df_news["Published"] >= start) & (df_news["Published"] <= end)]
        print(sliced_df.head(2))

        if not sliced_df.empty:
            filename_prefix = f"{label}_{trigger_time.strftime('%Y%m%dT%H%M')}"
            filepath = os.path.join(SLICE_DIR, f"rss_dumps/{filename_prefix}.csv")
            sliced_df.to_csv(filepath, index=False)
            saved_files.append({
                "filename": filepath,
                "prefix": filename_prefix,
                "label": label,
                "start": start,
                "end": end,
                "num_articles": len(sliced_df)
            })

    return saved_files



# ======================= MAIN =======================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trigger-time", type=str, default=None,
                        help="Timestamp in ISO format (e.g., 2025-05-28T12:00). If not set, uses current UTC time.")
    args = parser.parse_args()

    if args.trigger_time:
        trigger_time = datetime.fromisoformat(args.trigger_time).astimezone(timezone.utc)
        is_default_hourly = False
    else:
        trigger_time = datetime.utcnow()
        is_default_hourly = True

    digest_id = trigger_time.strftime('%Y%m%dT%H%M')

    hourly_dir = "./data/rss_slices/rss_hourly_dumps/"
    full_dir = "./data/rss_slices/rss_hourly_dumps/"
    output_dir = hourly_dir if is_default_hourly else full_dir
    os.makedirs(output_dir, exist_ok=True)

    # Fetch raw news but do not save with digest_id alone
    raw_filename = os.path.join(output_dir, f"rss_dumps_{digest_id}.csv")
    fetch_and_save_news(RSS_FEEDS, raw_filename, MAX_ARTICLES)
    df_news = load_rss_dataset(raw_filename)

    slices = compute_slices(trigger_time)

    saved = apply_slices(df_news, slices, trigger_time)

    print(f"✅ {len(saved)} archivos guardados: ")
    for s in saved:
        print(" -", s)
