
# %%
# df = pd.read_csv('./data/rss_slices/3day_window_20250530T1200.csv')


# # Save as JSONL
# output_path = './data/rss_slices/3day_window_20250530T1200.jsonl'
# df.to_json(output_path, orient='records', lines=True, force_ascii=False)

# %%
import pandas as pd
import numpy as np
import re
import glob
import os
import json

from utils import *


def split_topic_groups(df, min_rows=5, max_rows=25):
    result_frames = []

    for topic, group in df.groupby('Topic'):
        N = len(group)

        # Determine number of groups
        num_groups = max(1, int(np.ceil(N / max_rows)))
        split_size = int(np.ceil(N / num_groups))

        # print(topic, N, num_groups, split_size)

        # Safety check: if split_size too small, fallback to one group
        if split_size < min_rows:
            group = group.copy()
            group_id = f"01"
            group['GroupID'] = group_id
            result_frames.append(group)
        else:
            splits = np.array_split(group, num_groups)
            for i, split in enumerate(splits, start=1):
                split = split.copy()
                group_id = f"{i:02d}"
                split['GroupID'] = group_id
                result_frames.append(split)

    grouped_df = pd.concat(result_frames, ignore_index=True)
    return grouped_df


def sanitize_topic(topic):
    # Replace spaces and special characters with underscores
    return re.sub(r'[^\w\-]', '_', topic.strip().replace(' ', '_'))




# %%
import warnings

warnings.filterwarnings('ignore')


# ==== CONFIG ====
INPUT_DIR = './data/rss_slices/rss_dumps/'
OUTPUT_MD_DIR = './data/output_digests/'
OUTPUT_JSONL_DIR = './data/digest_jsonls/'
REQUIRED_COLS = ['Title', 'Source', 'Published']


# # Collect all CSVs in the input directory
# csv_files = glob.glob(os.path.join(INPUT_DIR, '*.csv'))
# print(len(csv_files))

import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--digest-id', type=str, default=None,
                        help="Digest ID like 20250611T15 (UTC hour)")
    parser.add_argument('--force', action='store_true',
                        help="Force regeneration even if JSONL exists")
    return parser.parse_args()


# import os
# import glob

# def parse_args():
#     parser = argparse.ArgumentParser(description="Generate markdown and JSONL digests for a given hour.")
#     parser.add_argument("--digest-id", type=str, default=None,
#                         help="UTC hour in format YYYYMMDDTHH (e.g., 20250611T09). Defaults to current UTC hour.")
#     parser.add_argument("--force", action="store_true",
#                         help="Force overwrite if digest already exists.")
#     return parser.parse_args()


# ==== MARKDOWN GENERATOR ====

def save_digest_files(df_grouped, output_dir, filename_prefix):
    os.makedirs(output_dir, exist_ok=True)
    group_metadata = []

    for (topic, group_id), group in df_grouped.groupby(['Topic', 'GroupID']):
        safe_topic = sanitize_topic(topic)
        filename = f"headlines_{filename_prefix}_{safe_topic}_{group_id}.md"
        filepath = os.path.join(output_dir, filename)

        content = f"# {topic} (Grupo {group_id})\n\n"
        for _, row in group.iterrows():
            article_id = row['article_id']
            title = row['Title']
            published = row.get('Published', '')
            source = row.get('Source', '')
            uid = row.get('uid', '')

            line = f"ID: {article_id} - Title: {title}"
            if published:
                try:
                    published_dt = pd.to_datetime(published)
                    line += f" _(Publicado: {published_dt.strftime('%Y-%m-%d %Hhs')})_"
                except Exception:
                    pass
            if source:
                line += f" — _Fuente: {source}_"
            if uid:
                line += f" — `uid:{uid}`"
            content += line + "\n"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        group_metadata.append({
            'group_id': group_id,
            'topic': topic,
            'filename': filename,
            'num_articles': len(group),
            'uids': group['uid'].tolist()
        })

    return group_metadata



# ==== JSONL EXPORTER ====

# data/rss_slices/2day_window_20250530T1200.csv [article_id, [Title, Source]] -- []

import re
import os
import json
import glob

def robust_parse_filename(filename):
    """
    Parse filenames like:
    headlines_2day_window_20250531T1200_Actividad_y_Empleo_01.md
    Returns a validated digest metadata dictionary.
    """
    base = os.path.basename(filename)
    match = re.match(
        # r'^headlines_([a-zA-Z0-9]+_window)_(\d{8}T\d{4})_(.+)_(\d{2})\.md$',
        r"^headlines_(\w+_window)_(\d{8}T\d{2})_(.+)_(\d{2})\.md$",
        base
    )
    if not match:
        raise ValueError(f"❌ Unexpected filename format: {filename}")

    window_type, datetime_str, topic_raw, group_number = match.groups()
    topic_raw = topic_raw.strip('_')  # Remove trailing underscores
    topic = topic_raw.replace('_', ' ')
    
    digest_group_id = f"{datetime_str}::{window_type}::{topic_raw}::{group_number}"

    return {
        "digest_group_id": digest_group_id,
        "digest_id": datetime_str,
        "window_type": window_type,
        "topic": topic,
        "group_number": group_number,
        "headlines_file": filename
    }

def create_digest_jsonl(input_dir, digest_id, output_file):
    """
    Parses all .md digest files in input_dir whose datetime string matches the full digest timestamp (e.g., 20250621T1400).
    """

    # Force canonical timestamp comparison (digest_id: hourly → T%H00)
    digest_id_full = digest_id #+ "00"

    all_md_files = sorted(glob.glob(os.path.join(input_dir, 'headlines_*.md')))
    matching_files = []

    for f in all_md_files:
        try:
            metadata = robust_parse_filename(f)

            if metadata['digest_id'] == digest_id_full:  # STRICT match
                matching_files.append((f, metadata))

        except Exception as e:
            print(f"⚠️ Skipped malformed filename {f}: {e}")
            continue

    print(f"📁 Found {len(matching_files)} digest files matching digest_id: {digest_id_full}")

    output_lines = []
    empty_or_invalid = 0

    for i, (filepath, meta) in enumerate(matching_files):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content or len(content) < 20:
                print(f"⚠️ Skipped empty or too-short file: {filepath}")
                empty_or_invalid += 1
                continue

            meta['id_digest'] = f"{digest_id_full}_{i:03d}"
            meta['content'] = content
            output_lines.append(json.dumps(meta, ensure_ascii=False))

        except Exception as e:
            print(f"❌ Error reading {filepath}: {e}")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as out_f:
        for line in output_lines:
            out_f.write(line + '\n')

    print(f"✅ Saved {len(output_lines)} JSONL entries to {output_file}")
    if empty_or_invalid:
        print(f"⚠️ {empty_or_invalid} files were skipped due to empty or invalid content.")


# ==== CORE WORKFLOW ====

def process_csv_file(csv_path):
    df = pd.read_csv(csv_path)

    # Validate structure
    for col in REQUIRED_COLS:
        if col not in df.columns:
            raise ValueError(f"Missing column {col} in {csv_path}")

    df['Published'] = pd.to_datetime(df['Published'], errors='coerce', utc=True)
    df = df.dropna(subset=['Published'])
    df = df.sort_values('Published').reset_index(drop=True)

    # Reassign stable article_id
    # df['article_id'] = df.index + 1

    if 'uid' not in df.columns:
        from hashlib import sha1
        def compute_uid(title, source):
            return sha1(f"{title}_{source}".encode("utf-8")).hexdigest()[:10]
        df['uid'] = df.apply(lambda row: compute_uid(row['Title'], row['Source']), axis=1)

    return df


from datetime import datetime, timezone

# ==== MAIN EXECUTION ====

def find_digest_csvs(input_dir, digest_hour_prefix):
    """
    Finds CSV files whose name includes a datetime that starts with digest_hour_prefix.
    For example: digest_hour_prefix = '20250611T12'
    """
    all_csvs = glob.glob(os.path.join(input_dir, '*.csv'))
    matched = [f for f in all_csvs if digest_hour_prefix in os.path.basename(f)]
    return matched

def main(args):
    ts = resolve_timestamps(args)
    digest_id = args.digest_id or ts['digest_id_h']
    print(f"\n🚀 [START] Digest generation for UTC hour: {digest_id}")

    os.makedirs(OUTPUT_JSONL_DIR, exist_ok=True)
    os.makedirs(OUTPUT_MD_DIR, exist_ok=True)

    jsonl_output = os.path.join(OUTPUT_JSONL_DIR, f'{digest_id}.jsonl')
    matching_jsonls = glob.glob(os.path.join(OUTPUT_JSONL_DIR, f"{digest_id}*.jsonl"))

    if matching_jsonls and not args.force:
        print(f"✅ JSONL already exists for {digest_id} → skipping digest creation.")
        return

    csv_files = find_digest_csvs(INPUT_DIR, digest_id)
    print(f"🔎 Located {len(csv_files)} CSV file(s) matching hour {digest_id} in {INPUT_DIR}")

    if not csv_files:
        print(f"⚠️ No matching CSVs found for digest_id {digest_id}. Exiting.")
        return

    total_groups = 0
    processed_count = 0
    all_md_paths = []

    for csv_file in csv_files:
        try:
            print(f"\n📄 Processing CSV: {csv_file}")
            df = process_csv_file(csv_file)
            print(f"📊 Loaded {len(df)} rows")

            df_grouped = split_topic_groups(df)
            if df_grouped.empty:
                print(f"⚠️ No topic groups found for: {csv_file} — skipping.")
                continue

            basename = os.path.splitext(os.path.basename(csv_file))[0]
            window_match = re.match(r"^([a-zA-Z0-9]+_window)_\d{8}T\d{4}$", basename)
            if not window_match:
                raise ValueError(f"❌ Unexpected CSV filename format: {basename}")

            window_type = window_match.group(1)
            filename_prefix = f"{window_type}_{digest_id}"

            group_metadata = save_digest_files(df_grouped, OUTPUT_MD_DIR, filename_prefix)

            if not group_metadata:
                print(f"⚠️ No markdown files created for: {csv_file}")
                continue

            for meta in group_metadata:
                path = os.path.join(OUTPUT_MD_DIR, meta['filename'])
                if os.path.exists(path):
                    all_md_paths.append(path)

            print(f"✅ Created {len(group_metadata)} digest(s) for prefix: {filename_prefix}")
            total_groups += len(group_metadata)
            processed_count += 1

        except Exception as e:
            print(f"❌ Error processing {csv_file}: {e}")

    if not all_md_paths:
        print(f"❌ No markdown digests found — aborting JSONL aggregation for {digest_id}")
        return

    print(f"\n🧩 Aggregating {len(all_md_paths)} .md files into JSONL for {digest_id}")
    create_digest_jsonl(OUTPUT_MD_DIR, digest_id, jsonl_output)
    print(f"\n🎉 Digest complete: {processed_count} file(s), {total_groups} groups → JSONL saved at {jsonl_output}")


# Entrypoint
if __name__ == "__main__":
    args = parse_args()

    if args.digest_id == "ALL":
        csv_files = glob.glob(os.path.join(INPUT_DIR, "*.csv"))
        digest_ids = sorted(set(
            re.search(r"_(\d{8}T\d{4})\.csv", os.path.basename(f)).group(1)
            for f in csv_files
            if re.search(r"_(\d{8}T\d{4})\.csv", os.path.basename(f))
        ))

        print(f"🔍 Found {len(digest_ids)} digest_id timestamps to process.")

        for did in digest_ids:
            print(f"\n--- Running digest for {did} ---")
            args.digest_id = did
            main(args)

    else:
        main(args)
