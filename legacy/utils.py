from datetime import datetime, timezone, timedelta
import argparse
import os
import json


# 1. State Registry: Track stage-by-stage completion

STATUS_DIR = "./data/status_logs"
os.makedirs(STATUS_DIR, exist_ok=True)

def get_status_path(digest_id_h):
    return os.path.join(STATUS_DIR, f"status_{digest_id_h}.json")

def load_status(digest_id_h):
    path = get_status_path(digest_id_h)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {"status": {}, "digest_id": digest_id_h}

def save_status(digest_id_h, status):
    path = get_status_path(digest_id_h)
    with open(path, 'w') as f:
        json.dump(status, f, indent=2)



def timestamp_from_digest_id(digest_id_h):
    # ts = datetime.strptime(digest_id_h, '%Y%m%dT%H').replace(tzinfo=timezone.utc)
    digest_id_h = digest_id_h.strip()
    fmt = '%Y%m%dT%H%M' if len(digest_id_h) == 13 else '%Y%m%dT%H'
    ts = datetime.strptime(digest_id_h, fmt).replace(tzinfo=timezone.utc)

    return {
        'trigger_time': ts.strftime('%Y-%m-%dT%H:%M'),
        'digest_id_h': digest_id_h,
        'digest_id_hm': ts.strftime('%Y%m%dT%H%M'),
        'day': ts.strftime('%Y-%m-%d'),
        'hour': ts.hour
    }

def digest_id_from_timestamp(ts):
    return ts.strftime("%Y%m%dT%H")



def find_missing_backfill_targets(hours=10):
    now = datetime.now(timezone.utc)
    targets = []
    for i in range(1, hours + 1):
        ts = now - timedelta(hours=i)
        digest_id_h = ts.strftime('%Y%m%dT%H')
        if not os.path.exists(get_status_path(digest_id_h)):
            targets.append(timestamp_from_digest_id(digest_id_h))
    return targets





def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--digest-id", type=str, default=None,
                        help="Digest ID in format YYYYMMDDTHH (e.g. 20250701T14)")
    parser.add_argument("--trigger-time", type=str, default=None,
                        help="ISO time (e.g. 2025-07-01T14:00). Used only if digest-id is not passed.")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def resolve_timestamps(args):
    if args.digest_id:
        return timestamp_from_digest_id(args.digest_id)
    elif args.trigger_time:
        dt = datetime.fromisoformat(args.trigger_time).astimezone(timezone.utc)
        return timestamp_from_digest_id(digest_id_from_timestamp(dt))
    else:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        return timestamp_from_digest_id(digest_id_from_timestamp(now))

