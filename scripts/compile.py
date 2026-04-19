"""
Compile daily conversation logs into structured knowledge articles.

This is the "LLM compiler" - it reads daily logs (source code) and produces
organized knowledge articles (the executable). Uses Azure OpenAI / OpenAI
for LLM calls and returns structured JSON that the script writes to disk.

Usage:
    uv run python scripts/compile.py                              # compile new/changed logs
    uv run python scripts/compile.py --all                        # force recompile everything
    uv run python scripts/compile.py --file daily/2026-04-18.md   # compile a specific log
    uv run python scripts/compile.py --dry-run                    # show what would be compiled
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from config import (
    AGENTS_FILE,
    CONCEPTS_DIR,
    CONNECTIONS_DIR,
    DAILY_DIR,
    KNOWLEDGE_DIR,
    LOG_FILE,
    INDEX_FILE,
    now_iso,
)
from utils import (
    file_hash,
    list_raw_files,
    list_wiki_articles,
    load_state,
    read_wiki_index,
    save_state,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


def compile_daily_log(log_path: Path, state: dict) -> None:
    """Compile a single daily log into knowledge articles via LLM."""
    from llm import chat

    log_content = log_path.read_text(encoding="utf-8")
    schema = AGENTS_FILE.read_text(encoding="utf-8")
    wiki_index = read_wiki_index()

    # Read existing articles for context
    existing_articles_context = ""
    existing = {}
    for article_path in list_wiki_articles():
        rel = article_path.relative_to(KNOWLEDGE_DIR)
        existing[str(rel)] = article_path.read_text(encoding="utf-8")

    if existing:
        parts = []
        for rel_path, content in existing.items():
            parts.append(f"### {rel_path}\n```markdown\n{content}\n```")
        existing_articles_context = "\n\n".join(parts)

    timestamp = now_iso()

    prompt = f"""You are a knowledge compiler. Read the daily conversation log and extract
knowledge into structured wiki articles.

## Schema (AGENTS.md)

{schema}

## Current Wiki Index

{wiki_index}

## Existing Wiki Articles

{existing_articles_context if existing_articles_context else "(No existing articles yet)"}

## Daily Log to Compile

**File:** {log_path.name}

{log_content}

## Your Task

Return a JSON object with this exact structure:

{{
  "articles": [
    {{
      "action": "create" or "update",
      "path": "concepts/slug-name.md" or "connections/slug-name.md",
      "content": "full markdown content including YAML frontmatter"
    }}
  ],
  "index_rows": [
    "| [[concepts/slug-name]] | One-line summary | daily/{log_path.name} | {timestamp[:10]} |"
  ],
  "log_entry": "markdown log entry for knowledge/log.md"
}}

### Rules:
1. Extract 3-7 distinct concepts worth their own article
2. Use the exact article format from AGENTS.md (YAML frontmatter + sections)
3. Include sources: in frontmatter pointing to daily/{log_path.name}
4. Use [[concepts/slug]] wikilinks to link related concepts
5. Write in encyclopedia style — neutral, comprehensive
6. Create connection articles if non-obvious relationships exist between 2+ concepts
7. If updating an existing article, include its FULL updated content (not just the diff)
8. For index_rows, include ONLY new entries (not already in the index)
9. For log_entry, use format: ## [{timestamp}] compile | {log_path.name}

If the daily log contains nothing worth extracting, return:
{{"articles": [], "index_rows": [], "log_entry": "## [{timestamp}] compile | {log_path.name}\\n- Source: daily/{log_path.name}\\n- Result: nothing worth extracting"}}
"""

    messages = [
        {"role": "system", "content": "You are a precise knowledge compiler. Always return valid JSON."},
        {"role": "user", "content": prompt},
    ]

    try:
        response_text = chat(messages, json_mode=True, max_tokens=16000)
        result = json.loads(response_text)
    except (json.JSONDecodeError, Exception) as e:
        print(f"  Error: {e}")
        return

    # Write articles
    articles_created = []
    articles_updated = []

    for article in result.get("articles", []):
        action = article.get("action", "create")
        rel_path = article.get("path", "")
        content = article.get("content", "")

        if not rel_path or not content:
            continue

        full_path = KNOWLEDGE_DIR / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

        if action == "update":
            articles_updated.append(f"[[{rel_path.replace('.md', '')}]]")
        else:
            articles_created.append(f"[[{rel_path.replace('.md', '')}]]")

        print(f"    {action}: {rel_path}")

    # Append new rows to index
    index_rows = result.get("index_rows", [])
    if index_rows:
        with open(INDEX_FILE, "a", encoding="utf-8") as f:
            for row in index_rows:
                f.write(row.rstrip() + "\n")

    # Append to build log
    log_entry = result.get("log_entry", "")
    if log_entry:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n" + log_entry + "\n")

    # Update state
    rel = log_path.name
    state.setdefault("ingested", {})[rel] = {
        "hash": file_hash(log_path),
        "compiled_at": now_iso(),
    }
    save_state(state)

    created_str = ", ".join(articles_created) if articles_created else "none"
    updated_str = ", ".join(articles_updated) if articles_updated else "none"
    print(f"  Created: {created_str}")
    print(f"  Updated: {updated_str}")


def main():
    parser = argparse.ArgumentParser(description="Compile daily logs into knowledge articles")
    parser.add_argument("--all", action="store_true", help="Force recompile all logs")
    parser.add_argument("--file", type=str, help="Compile a specific daily log file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be compiled")
    args = parser.parse_args()

    state = load_state()

    if args.file:
        target = Path(args.file)
        if not target.is_absolute():
            target = DAILY_DIR / target.name
        if not target.exists():
            target = ROOT_DIR / args.file
        if not target.exists():
            print(f"Error: {args.file} not found")
            sys.exit(1)
        to_compile = [target]
    else:
        all_logs = list_raw_files()
        if args.all:
            to_compile = all_logs
        else:
            to_compile = []
            for log_path in all_logs:
                rel = log_path.name
                prev = state.get("ingested", {}).get(rel, {})
                if not prev or prev.get("hash") != file_hash(log_path):
                    to_compile.append(log_path)

    if not to_compile:
        print("Nothing to compile — all daily logs are up to date.")
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Files to compile ({len(to_compile)}):")
    for f in to_compile:
        print(f"  - {f.name}")

    if args.dry_run:
        return

    for i, log_path in enumerate(to_compile, 1):
        print(f"\n[{i}/{len(to_compile)}] Compiling {log_path.name}...")
        compile_daily_log(log_path, state)
        print(f"  Done.")

    articles = list_wiki_articles()
    print(f"\nCompilation complete. Knowledge base: {len(articles)} articles")


if __name__ == "__main__":
    main()
