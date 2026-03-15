import fs from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";

export async function GET() {
  const cwd = process.cwd();
  const publicData = path.join(cwd, "public", "data");

  const refsPath = path.join(publicData, "news_recent_refs_latest.jsonl");
  const groupsPath = path.join(publicData, "news_recent_groups_latest.jsonl");
  const editorialPath = path.join(publicData, "editorial_latest.json");

  const payload = {
    cwd,
    publicData,
    refsExists: fs.existsSync(refsPath),
    groupsExists: fs.existsSync(groupsPath),
    editorialExists: fs.existsSync(editorialPath),
    refsPreview: fs.existsSync(refsPath)
      ? fs.readFileSync(refsPath, "utf-8").split("\n").filter(Boolean).slice(0, 2)
      : [],
    groupsPreview: fs.existsSync(groupsPath)
      ? fs.readFileSync(groupsPath, "utf-8").split("\n").filter(Boolean).slice(0, 2)
      : [],
    editorialPreview: fs.existsSync(editorialPath)
      ? JSON.parse(fs.readFileSync(editorialPath, "utf-8"))
      : null,
  };

  return NextResponse.json(payload);
}
