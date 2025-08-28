#!/usr/bin/env python3

import os
import glob
import pandas as pd
import hashlib

# Configurations
RSS_DIR = '/home/matias/Documents/media_monitor/data/rss_slices/'
MASTER_INDEX_PATH = './data/master_index.csv'
PROCESSED_FILES_LOG = './data/processed_files.txt'
DATA_DIR = './data/'

# Ensure output directory exists
os.makedirs(DATA_DIR, exist_ok=True)



def compute_short_hash(text):
    """Compute a short hash of a text (Title + Source)."""
    h = hashlib.sha1(text.encode('utf-8')).hexdigest()
    return h[:8]

def process_csv_file(csv_path):
    """Load a CSV and return a DataFrame with index_id added, reusing uid if available."""
    df = pd.read_csv(csv_path)

    # Drop rows with missing Title or Source
    df = df.dropna(subset=['Title', 'Source'])

    if 'uid' in df.columns:
        df['index_id'] = df['uid']
    else:
        df['index_id'] = df.apply(lambda row: compute_short_hash(row['Title'] + row['Source']), axis=1)

    return df


def load_master_index(path):
    """Load the master index CSV if it exists, else return an empty DataFrame."""
    if os.path.exists(path):
        master_df = pd.read_csv(path)
    else:
        master_df = pd.DataFrame()
    return master_df

def save_master_index(master_df, path):
    """Save the master index to a CSV."""
    master_df.to_csv(path, index=False)
    print(f"✅ Master index saved at {path} with {len(master_df)} articles.")

def load_processed_files(log_path):
    """Load the list of processed files to avoid reprocessing."""
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f)
    else:
        return set()

def save_processed_files(processed_files, log_path):
    """Save the updated list of processed files."""
    with open(log_path, 'w', encoding='utf-8') as f:
        for filename in processed_files:
            f.write(f"{filename}\n")

def update_master_index_from_directory(rss_dir, master_index_path, processed_files_log):
    master_df = load_master_index(master_index_path)
    processed_files = load_processed_files(processed_files_log)

    new_files = []
    for csv_file in sorted(glob.glob(os.path.join(rss_dir, '**/*.csv'), recursive=True)):
        rel_path = os.path.relpath(csv_file, start=rss_dir)
        if rel_path not in processed_files:
            new_files.append((csv_file, rel_path))


    if not new_files and master_df.shape[0] > 0:
        print("✅ No new CSV files to process. Master index is up-to-date.")
        return

    new_dfs = []
    for file, rel_path in new_files:
        print(f"📥 Processing new file: {rel_path}")
        df = process_csv_file(file)
        new_dfs.append(df)
        processed_files.add(rel_path)


    if new_dfs:
        new_data_df = pd.concat(new_dfs, ignore_index=True)
    else:
        new_data_df = pd.DataFrame()

    # combined_df = pd.concat([new_data_df, master_df], ignore_index=True)
    # combined_df = combined_df.drop_duplicates(subset=['Title', 'Source'], keep='first')


    combined_df = pd.concat([new_data_df, master_df], ignore_index=True)

    if combined_df.empty:
        print("⚠️ Combined DataFrame is empty. No articles to process.")
        return

    if 'Published' not in combined_df.columns:
        print("⚠️ 'Published' column missing in combined DataFrame. Check input CSVs.")
        print("Columns found:", combined_df.columns.tolist())
        return

    # Parse Published date
    combined_df['Published'] = pd.to_datetime(combined_df['Published'], errors='coerce')
    combined_df = combined_df.sort_values('Published', ascending=False)

    # Drop duplicates on Title and Source (keeping most recent)
    if 'Title' not in combined_df.columns or 'Source' not in combined_df.columns:
        print("⚠️ Missing 'Title' or 'Source' columns. Check input CSVs.")
        print("Columns found:", combined_df.columns.tolist())
        return

    # deduped_df = combined_df.drop_duplicates(subset=['Title', 'Source'], keep='first')
    deduped_df = combined_df.drop_duplicates(subset=['index_id'], keep='first')

    assert deduped_df['index_id'].is_unique, "❌ Duplicate index_id found in deduped output."

    # Select relevant columns only
    columns_to_keep = ['index_id', 'uid', 'Topic', 'Title', 'Published', 'Source', 'Link']
    deduped_df = deduped_df[[col for col in columns_to_keep if col in deduped_df.columns]]


    # Save final master index
    save_master_index(deduped_df, master_index_path)
    save_processed_files(processed_files, processed_files_log)



def main():
    update_master_index_from_directory(RSS_DIR, MASTER_INDEX_PATH, PROCESSED_FILES_LOG)

if __name__ == "__main__":
    main()
