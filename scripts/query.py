"""
Query the knowledge base using index-guided retrieval.

The LLM reads the index, picks relevant articles, and synthesizes an answer.
No vector database, no embeddings — just structured markdown and an index
the LLM can reason over.

Usage:
    uv run python scripts/query.py "How should I handle auth redirects?"
    uv run python scripts/query.py "What patterns do I use?" --file-back
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from config import KNOWLEDGE_DIR, QA_DIR, INDEX_FILE, LOG_FILE, now_iso
from utils import load_state, read_all_wiki_content, save_state, slugify

ROOT_DIR = Path(__file__).resolve().parent.parent


def run_query(question: str, file_back: bool = False) -> str:
    """Query the knowledge base and optionally file the answer back."""
    from llm import chat

    wiki_content = read_all_wiki_content()
    timestamp = now_iso()

    file_back_instructions = ""
    if file_back:
        file_back_instructions = f"""

After answering, also include a "filed_article" key in your JSON with:
- "slug": a filename-safe slug for the question
- "content": full markdown Q&A article with YAML frontmatter (title, question, consulted, filed date)
- "index_row": index table row for this Q&A article
- "log_entry": log.md entry
"""

    prompt = f"""You are a knowledge base query engine. Answer the user's question by
consulting the knowledge base below.

## How to Answer

1. Read the INDEX section — it lists every article with a summary
2. Identify relevant articles from the index
3. Read those articles carefully (included below)
4. Synthesize a clear, thorough answer
5. Cite sources using [[wikilinks]] (e.g., [[concepts/supabase-auth]])
6. If the knowledge base doesn't contain relevant information, say so

## Knowledge Base

{wiki_content}

## Question

{question}

Return a JSON object:
{{
  "answer": "your synthesized answer with [[wikilinks]]",
  "consulted": ["concepts/article-1", "concepts/article-2"]
  {', "filed_article": {{ "slug": "...", "content": "...", "index_row": "...", "log_entry": "..." }}' if file_back else ''}
}}
{file_back_instructions}"""

    messages = [
        {"role": "system", "content": "You are a knowledge base query engine. Return valid JSON."},
        {"role": "user", "content": prompt},
    ]

    try:
        response_text = chat(messages, json_mode=True)
        result = json.loads(response_text)
    except (json.JSONDecodeError, Exception) as e:
        return f"Error querying knowledge base: {e}"

    answer = result.get("answer", "No answer generated.")

    # File back if requested
    if file_back and "filed_article" in result:
        filed = result["filed_article"]
        slug = filed.get("slug", slugify(question[:60]))
        content = filed.get("content", "")
        index_row = filed.get("index_row", "")
        log_entry = filed.get("log_entry", "")

        if content:
            QA_DIR.mkdir(parents=True, exist_ok=True)
            qa_path = QA_DIR / f"{slug}.md"
            qa_path.write_text(content, encoding="utf-8")

        if index_row:
            with open(INDEX_FILE, "a", encoding="utf-8") as f:
                f.write(index_row.rstrip() + "\n")

        if log_entry:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write("\n" + log_entry + "\n")

    # Update state
    state = load_state()
    state["query_count"] = state.get("query_count", 0) + 1
    save_state(state)

    return answer


def main():
    parser = argparse.ArgumentParser(description="Query the personal knowledge base")
    parser.add_argument("question", help="The question to ask")
    parser.add_argument(
        "--file-back",
        action="store_true",
        help="File the answer back as a Q&A article",
    )
    args = parser.parse_args()

    print(f"Question: {args.question}")
    print(f"File back: {'yes' if args.file_back else 'no'}")
    print("-" * 60)

    answer = run_query(args.question, file_back=args.file_back)
    print(answer)

    if args.file_back:
        print("\n" + "-" * 60)
        qa_count = len(list(QA_DIR.glob("*.md"))) if QA_DIR.exists() else 0
        print(f"Answer filed to knowledge/qa/ ({qa_count} Q&A articles total)")


if __name__ == "__main__":
    main()
