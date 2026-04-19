"""
Harvest conversations from the Copilot CLI session store into daily logs.

Reads ~/.copilot/session-store.db, extracts sessions and turns since the
last harvest, and writes them into daily/*.md files.

Usage:
    uv run python scripts/harvest.py              # harvest new sessions only
    uv run python scripts/harvest.py --all         # re-harvest everything
    uv run python scripts/harvest.py --dry-run     # show what would be harvested
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from config import DAILY_DIR, SESSION_STORE_DB, now_iso
from utils import load_state, save_state

MAX_MSG_CHARS = 1500


def connect_session_store() -> sqlite3.Connection:
    """Open the Copilot CLI session store in read-only mode."""
    if not SESSION_STORE_DB.exists():
        print(f"Error: session store not found at {SESSION_STORE_DB}")
        sys.exit(1)
    conn = sqlite3.connect(f"file:{SESSION_STORE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 3000")
    return conn


def truncate(text: str | None, max_chars: int = MAX_MSG_CHARS) -> str:
    """Truncate text, preserving meaningful content."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def format_session_entry(session: sqlite3.Row, turns: list[sqlite3.Row]) -> str:
    """Format a session and its turns into a daily log entry."""
    session_time = session["created_at"][11:16] if session["created_at"] else "??:??"
    summary = session["summary"] or "Untitled Session"
    cwd = session["cwd"] or ""
    repo = session["repository"] or ""

    lines = [f"### Session ({session_time}) - {summary}", ""]

    # Context line
    context_parts = []
    if repo:
        context_parts.append(f"repo: {repo}")
    if cwd:
        context_parts.append(f"cwd: {cwd}")
    if context_parts:
        lines.append(f"**Context:** {', '.join(context_parts)}")
        lines.append("")

    # Key exchanges
    lines.append("**Key Exchanges:**")
    for turn in turns:
        user_msg = truncate(turn["user_message"])
        asst_msg = truncate(turn["assistant_response"])

        if user_msg:
            # Skip skill-context and system messages
            if user_msg.startswith("<skill-context") or user_msg.startswith("<system"):
                continue
            lines.append(f"- **User:** {user_msg}")
        if asst_msg:
            lines.append(f"- **Assistant:** {asst_msg}")

    lines.append("")
    return "\n".join(lines)


def harvest_sessions(force_all: bool = False, dry_run: bool = False) -> int:
    """Harvest sessions from the Copilot CLI session store."""
    state = load_state()
    last_harvest = state.get("last_harvest", {})
    cursor_ts = "1970-01-01T00:00:00Z" if force_all else last_harvest.get("timestamp", "1970-01-01T00:00:00Z")
    harvested_ids = set() if force_all else set(last_harvest.get("harvested_ids", []))

    conn = connect_session_store()

    # Get sessions since last harvest that have turns
    sessions = conn.execute("""
        SELECT s.id, s.cwd, s.repository, s.branch, s.summary, s.created_at
        FROM sessions s
        WHERE s.created_at > ?
        AND EXISTS (SELECT 1 FROM turns t WHERE t.session_id = s.id)
        ORDER BY s.created_at
    """, (cursor_ts,)).fetchall()

    # Filter out already-harvested sessions (robust dedup)
    new_sessions = [s for s in sessions if s["id"] not in harvested_ids]

    if not new_sessions:
        print("Nothing to harvest — all sessions are up to date.")
        conn.close()
        return 0

    print(f"{'[DRY RUN] ' if dry_run else ''}Sessions to harvest: {len(new_sessions)}")

    # Group sessions by date
    daily_entries: dict[str, list[str]] = defaultdict(list)
    latest_ts = cursor_ts
    new_ids = []

    for session in new_sessions:
        session_date = session["created_at"][:10]

        turns = conn.execute("""
            SELECT turn_index, user_message, assistant_response, timestamp
            FROM turns WHERE session_id = ? ORDER BY turn_index
        """, (session["id"],)).fetchall()

        if not turns:
            continue

        summary_line = session["summary"] or "Untitled"
        print(f"  - {session_date} | {summary_line} ({len(turns)} turns)")

        if not dry_run:
            entry = format_session_entry(session, turns)
            daily_entries[session_date].append(entry)

        new_ids.append(session["id"])
        if session["created_at"] > latest_ts:
            latest_ts = session["created_at"]

    conn.close()

    if dry_run:
        return len(new_sessions)

    # Write to daily log files
    for date, entries in sorted(daily_entries.items()):
        write_daily_log(date, entries)

    # Update state with composite cursor
    all_harvested = list(harvested_ids | set(new_ids))
    # Keep only last 200 IDs to prevent unbounded growth
    if len(all_harvested) > 200:
        all_harvested = all_harvested[-200:]

    state["last_harvest"] = {
        "timestamp": latest_ts,
        "harvested_ids": all_harvested,
    }
    save_state(state)

    print(f"\nHarvested {len(new_sessions)} sessions into {len(daily_entries)} daily log(s).")
    return len(new_sessions)


def write_daily_log(date: str, entries: list[str]) -> None:
    """Write or append entries to a daily log file."""
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    log_path = DAILY_DIR / f"{date}.md"

    if not log_path.exists():
        header = f"# Daily Log: {date}\n\n## Sessions\n\n"
        log_path.write_text(header, encoding="utf-8")

    with open(log_path, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(entry + "\n")


def main():
    parser = argparse.ArgumentParser(description="Harvest Copilot CLI sessions into daily logs")
    parser.add_argument("--all", action="store_true", help="Re-harvest all sessions")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be harvested")
    args = parser.parse_args()

    count = harvest_sessions(force_all=args.all, dry_run=args.dry_run)
    if count > 0 and not args.dry_run:
        print(f"Daily logs written to: {DAILY_DIR}/")


if __name__ == "__main__":
    main()
