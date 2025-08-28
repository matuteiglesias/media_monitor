# 00_daemon.py

import time
import os
import subprocess
import argparse
from datetime import datetime, timezone, timedelta
import json

from utils import *

## STAGED
# 2. Per-Stage Execution with Skip Logic

def get_stages(ts):
    return [
        {"name": "01_digests", "cmd": ["python", "01_digests.py", "--trigger-time"]},
        {"name": "02_index", "cmd": ["python", "02_master_index_update.py"]},
        {"name": "03_digest", "cmd": ["python", "03_headlines_digests.py", "--digest-id"]},
        {"name": "04_promptflow", "cmd": ["python", "04_promptflow_run.py", "--digest-id"]},
        {"name": "05_explode_pf", "cmd": ["python", "05_explode_pf_outputs.py"]},
        {"name": "06_scrape", "cmd": ["python", "06_scrape_contents.py", "--day", "--hour"]},  # ← optional
    ]

def run_pipeline_staged(ts):
    STAGES = get_stages(ts)  # build stage commands using current ts
    status = load_status(ts['digest_id_h'])
    for stage in STAGES:
        name = stage["name"]
        if status["status"].get(name) == "ok":
            print(f"⏩ Skipping {name} (already completed)")
            continue
        try:
            cmd = list(stage["cmd"])  # Clone
            if "--trigger-time" in cmd:
                cmd.append(ts["trigger_time"])
            elif "--digest-id" in cmd:
                cmd.append(ts["digest_id_h"])
            elif "--day" in cmd:
                cmd.append(ts["day"])
                cmd.append("--hour")
                cmd.append(str(ts["hour"]))

            print(f"🚀 Running stage: {name}")
            log_message(ts["digest_id_h"], f"Running stage {name}...")

            subprocess.run(cmd, check=True)
            status["status"][name] = "ok"
        except subprocess.CalledProcessError as e:
            status["status"][name] = f"fail ({e.returncode})"
            save_status(ts["digest_id_h"], status)
            print(f"❌ Stage {name} failed: {e}")
            return False  # stop pipeline
    save_status(ts["digest_id_h"], status)
    print(f"✅ All stages completed for {ts['digest_id_h']}")
    return True


## NOT STAGED


def current_timestamps():
    now = datetime.now(timezone.utc)
    return {
        'trigger_time': now.strftime('%Y-%m-%dT%H:%M'),
        'digest_id_h': now.strftime('%Y%m%dT%H'),
        'digest_id_hm': now.strftime('%Y%m%dT%H%M'),
        'day': now.strftime('%Y-%m-%d'),
        'hour': now.hour
    }

def already_processed(digest_id_h):
    return os.path.exists(f"./data/digest_jsonls/{digest_id_h}.jsonl")

def fully_processed(digest_id_h):
    status = load_status(digest_id_h)
    STAGES = get_stages(digest_id_h)
    return all(status["status"].get(s["name"]) == "ok" for s in STAGES)



# def run_pipeline(ts):
#     print(f"🚀 Starting pipeline for: {ts['digest_id_h']}")

#     subprocess.run([
#         "python", "01_digests.py",
#         "--trigger-time", ts['trigger_time']
#     ], check=True)

#     subprocess.run([
#         "python", "02_master_index_update.py"
#     ], check=True)

#     subprocess.run([
#         "python", "03_headlines_digests.py",
#         "--digest-id", ts['digest_id_h']
#     ], check=True)

#     subprocess.run([
#         "python", "04_scrape_contents.py",
#         "--day", ts['day'],
#         "--hour", str(ts['hour'])
#     ], check=True)

#     print(f"✅ Done with: {ts['digest_id_h']}\n")



def daemon_loop(interval_minutes=5, backfill_hours=0):
    seen = set()

    # Generate list of past hours
    backfill_targets = find_missing_backfill_targets(hours=backfill_hours)
    # backfill_targets = []
    # now = datetime.now(timezone.utc)
    # for i in range(1, backfill_hours + 1):
    #     ts = now - timedelta(hours=i)
    #     backfill_targets.append({
    #         'trigger_time': ts.strftime('%Y-%m-%dT%H:%M'),
    #         'digest_id_h': ts.strftime('%Y%m%dT%H'),
    #         'digest_id_hm': ts.strftime('%Y%m%dT%H%M'),
    #         'day': ts.strftime('%Y-%m-%d'),
    #         'hour': ts.hour
    #     })

    while True:
        ts = current_timestamps()

        if ts['digest_id_h'] not in seen and not fully_processed(ts['digest_id_h']):
            try:
                # run_pipeline(ts)  ##
                run_pipeline_staged(ts)  ##
                seen.add(ts['digest_id_h'])
            except subprocess.CalledProcessError as e:
                print(f"❌ Pipeline failed for {ts['digest_id_h']}: {e}")
            except Exception as e:
                print(f"💥 Unexpected error: {e}")

        elif backfill_targets:
            bts = backfill_targets[0]
            if bts['digest_id_h'] not in seen and not fully_processed(bts['digest_id_h']):
                

                try:
                    # run_pipeline(bts)
                    run_pipeline_staged(bts)
                    seen.add(bts['digest_id_h'])
                except subprocess.CalledProcessError as e:
                    print(f"❌ Backfill failed for {bts['digest_id_h']}: {e}")
                except Exception as e:
                    print(f"💥 Backfill error: {e}")
                backfill_targets.pop(0)
            else:
                print(f"⏭️  Skipping backfill {bts['digest_id_h']} (already seen or processed)")
                backfill_targets.pop(0)

        
        else:
            print(f"⏳ Already processed {ts['digest_id_h']} — sleeping...")

        time.sleep(interval_minutes * 60)

# 4. Logging
LOG_DIR = "./data/logs"
os.makedirs(LOG_DIR, exist_ok=True)

def log_message(digest_id, message):
    log_path = os.path.join(LOG_DIR, f"log_{digest_id}.txt")
    with open(log_path, 'a') as f:
        timestamp = datetime.now(timezone.utc).isoformat()
        f.write(f"[{timestamp}] {message}\n")



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--backfill', type=int, default=0, help="How many past hours to process")
    parser.add_argument('--digest-id', type=str, help="Run pipeline for a specific digest ID (format: YYYYMMDDTHH)")
    args = parser.parse_args()

    if args.digest_id:
        ts = timestamp_from_digest_id(args.digest_id)
        run_pipeline_staged(ts)
    else:
        daemon_loop(interval_minutes=1, backfill_hours=args.backfill)