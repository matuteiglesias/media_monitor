#!/usr/bin/env python
import argparse, os, json, sys
from backend import db

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', required=True, choices=['scrape','promptflow','explode','generate','publish'])
    ap.add_argument('--key', help='work key (e.g., index_id or digest id)')
    ap.add_argument('--from-quarantine', help='path to a quarantined JSONL; use record i')
    ap.add_argument('--i', type=int, default=0)
    args = ap.parse_args()

    if args.from_quarantine:
        with open(args.from_quarantine, 'r') as f:
            lines = f.readlines()
        rec = json.loads(lines[args.i])
        payload = rec.get('job', {}).get('payload') or rec.get('payload') or rec
        key = rec.get('job', {}).get('work_key') or payload.get('index_id') or payload.get('digest_id_hour')
        db.push_work(args.stage, key, payload)   # re-enqueue once
        print(f"[replay] re-enqueued {args.stage} key={key}")
        sys.exit(0)

    if not args.key:
        print("--key is required if not using --from-quarantine", file=sys.stderr)
        sys.exit(1)
    # Look up last failure and re-enqueue (simple version)
    db.requeue_one(args.stage, args.key)  # implement a trivial helper server-side
    print(f"[replay] re-enqueued {args.stage} key={args.key}")

if __name__ == "__main__":
    main()