#!/usr/bin/env python3

import os
import time
import json
import pyperclip
import pandas as pd
from tqdm import tqdm
from hashlib import sha1
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# === Configuración ===
ARTICLE_FILE = "./data/article_quotes/articles_to_scrape.jsonl"
SCRAPED_LOG_PATH = "./data/scraped_links.jsonl"
SLEEP_TIME = 5
PAGE_TIMEOUT = 15

def compute_uid(title, source):
    return sha1(f"{title}_{source}".encode("utf-8")).hexdigest()[:10]



# === Cargar set de index_ids ya scrapeados ===
def load_scraped_ids(path):
    if not os.path.exists(path):
        return set()
    scraped = set()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line)
                scraped.add(record.get('index_id'))
            except Exception as e:
                print(f"⚠️ JSONL parsing failed: {e}")
    return scraped

# def load_scraped_uids(path):
#     if not os.path.exists(path):
#         return set()
#     scraped = set()
#     with open(path, 'r', encoding='utf-8') as f:
#         for line in f:
#             try:
#                 record = json.loads(line)
#                 scraped.add(record.get('uid') or record.get('index_id'))
#             except Exception as e:
#                 print(f"⚠️ JSONL parsing failed: {e}")
#     return scraped


def scrape_article(row):
    options = Options()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")

    driver = None
    result = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(PAGE_TIMEOUT)
        driver.get(row['Link'])
        time.sleep(SLEEP_TIME)

        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.CONTROL, 'a')
        body.send_keys(Keys.CONTROL, 'c')
        time.sleep(1)

        raw_html = pyperclip.paste()

        result = row.to_dict()
        result['Published'] = result['Published'].isoformat() if isinstance(result['Published'], pd.Timestamp) else result['Published']
        result['scraped_data'] = raw_html
        print(f"✅ Scraped: {row['Link']}")

    except Exception as e:
        print(f"⚠️ Error on {row['Link']}: {e}")
    finally:
        if driver:
            driver.quit()

    return result


def append_scraped(records, path):
    with open(path, 'a', encoding='utf-8') as f:
        for record in records:
            json.dump(record, f, ensure_ascii=False)
            f.write('\n')

import os
import pandas as pd
from datetime import datetime, timezone
from tqdm import tqdm
# from utils import compute_uid, load_scraped_uids, scrape_article, append_scraped

# # Nuevo input: dataset post-PF
# ARTICLE_FILE = "./data/article_quotes/articles_to_scrape.csv"
# SCRAPED_LOG_PATH = "./data/scraped_links.jsonl"


# === Main ===
def main():
    if not os.path.exists(ARTICLE_FILE):
        print(f"❌ No article dataset at {ARTICLE_FILE}")
        return

    df = pd.read_json(ARTICLE_FILE, lines=True)
    if df.empty or 'index_id' not in df.columns:
        print("⚠️ Article dataset missing required fields.")
        return

    print(f"📄 Cargados {len(df)} artículos desde {ARTICLE_FILE}")

    # Asegurarse de que index_id sea string (por seguridad en merge y hash sets)
    df['index_id'] = df['index_id'].astype(str)

    # Cargar ids ya scrapeados
    scraped_ids = load_scraped_ids(SCRAPED_LOG_PATH)

    # Filtrar artículos no scrapeados
    to_scrape = df[~df['index_id'].isin(scraped_ids)]
    print(f"🚀 A scrapear: {len(to_scrape)} artículos (capped at 500)")
    to_scrape = to_scrape.sort_values('Published', ascending = False)
    to_scrape = to_scrape.head(50)

    for _, row in tqdm(to_scrape.iterrows(), total=len(to_scrape)):
        result = scrape_article(row)
        if result:
            append_scraped([result], SCRAPED_LOG_PATH)

    print("✅ Scraping finished.")



# === CLI ===
if __name__ == "__main__":
    try:
        get_ipython
        IN_JUPYTER = True
    except NameError:
        IN_JUPYTER = False

    if IN_JUPYTER:
        print("⚠️ Jupyter mode detected.")
        main()
    else:
        # Sin argumentos CLI, ejecuta directamente sobre todo el archivo
        main()
