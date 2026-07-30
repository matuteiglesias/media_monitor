#!/usr/bin/env python3
"""Validate canonical documentation metadata, relative links, and naming rules."""
from pathlib import Path
import re, sys
ROOT=Path(__file__).resolve().parents[1]
CANON=("architecture","components","operations","reference","case-studies","maintenance")
files=[ROOT/"README.md",ROOT/"AGENTS.md",*sorted((ROOT/"docs").rglob("*.md"))]
errors=[]
for p in files:
 text=p.read_text(encoding="utf-8")
 rel=p.relative_to(ROOT)
 if len(rel.parts)>1 and rel.parts[0]=="docs" and rel.parts[1] in CANON and "**Status:**" not in text[:500]:
  errors.append(f"{rel}: canonical page lacks Status metadata")
 if len(rel.parts)>2 and rel.parts[0]=="docs" and rel.parts[1] in CANON and re.match(r"pr\d",p.name,re.I):
  errors.append(f"{rel}: canonical filename must be capability-oriented")
 for target in re.findall(r"\[[^]]*\]\(([^)]+)\)",text):
  if target.startswith(("http://","https://","mailto:","#")): continue
  path=target.split("#",1)[0]
  if path and not (p.parent/path).resolve().exists(): errors.append(f"{rel}: broken link {target}")
 if "```mermaid" in text and not re.search(r"```mermaid[\s\S]*?```\s*\n\s*\S",text): errors.append(f"{rel}: Mermaid diagram lacks text explanation")
if errors:
 print("\n".join(errors),file=sys.stderr);raise SystemExit(1)
print(f"docs-check: {len(files)} Markdown files passed")
