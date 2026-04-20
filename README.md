# Copilot Memory Compiler

**Your GitHub Copilot CLI conversations compile themselves into a searchable knowledge base.**

Adapted from [Karpathy's LLM Knowledge Base](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) architecture and [coleam00's Claude Code implementation](https://github.com/coleam00/claude-memory-compiler), but built for **GitHub Copilot CLI** instead of Claude Code.

Instead of RAG — where the LLM re-discovers knowledge from scratch on every question — this system **incrementally compiles a persistent wiki** from your conversations. Cross-references are pre-built. Contradictions are pre-flagged. Synthesis compounds with every session. The wiki is a persistent, compounding artifact.

> *"The wiki is the codebase; the LLM is the programmer; Obsidian is the IDE."*
> — Andrej Karpathy

* [Two Tools, Two Roles](#two-tools-two-roles)
* [What You Need](#what-you-need)
* [How It Works](#how-it-works)
* [Architecture](#architecture)
* [Getting Started](#getting-started)
  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
  * [Configuration](#configuration)
* [Usage](#usage)
  * [Harvest Sessions](#harvest-sessions)
  * [Compile Knowledge](#compile-knowledge)
  * [Query the Knowledge Base](#query-the-knowledge-base)
  * [Lint (Health Checks)](#lint-health-checks)
  * [Full Pipeline](#full-pipeline)
* [Why Not RAG?](#why-not-rag)
* [Project Structure](#project-structure)
* [How It Differs from the Claude Code Version](#how-it-differs-from-the-claude-code-version)
* [Customization](#customization)
* [Costs](#costs)
* [Contributing](#contributing)
* [License](#license)

## Two Tools, Two Roles

This project uses **two separate tools** for different purposes:

| Tool | Role | What It Does |
|------|------|-------------|
| **GitHub Copilot CLI** | Data source + injection | Where you have conversations. Stores session history in a local SQLite database. Knowledge gets injected back via `.github/copilot-instructions.md`. |
| **Azure OpenAI / OpenAI** | Compilation engine | The LLM brain that reads raw conversation logs and compiles them into structured wiki articles. Also powers queries and lint checks. |

**Why both?** In the original [Claude Code version](https://github.com/coleam00/claude-memory-compiler), Claude does everything — it's both the conversation tool *and* the compilation engine (via the Agent SDK). GitHub Copilot CLI doesn't expose an agent SDK, so we split the roles: Copilot CLI handles the data pipeline (capture → inject), and Azure OpenAI handles the LLM heavy lifting (compile → query).

## What You Need

| Requirement | What It Is | Required? |
|-------------|-----------|-----------|
| **GitHub Copilot CLI** | Terminal AI assistant ([copilot in the CLI](https://docs.github.com/en/copilot/github-copilot-in-the-cli)) — requires a GitHub Copilot subscription (Individual, Business, or Enterprise) | **Yes** — this is where your conversation data comes from |
| **Azure OpenAI or OpenAI API key** | LLM API access for compilation, queries, and lint | **Yes** — needed for `compile.py`, `query.py`, and `lint.py` |
| **Python 3.12+** | Runtime (auto-managed by uv) | **Yes** — uv downloads it automatically if missing |

> **Cost note:** You need both a GitHub Copilot subscription *and* an Azure OpenAI / OpenAI API key. The Copilot subscription covers your conversations; the API key covers compilation. Harvesting is always free (local SQLite read).

## How It Works

```
Copilot CLI sessions (automatic)
    → harvest.py reads ~/.copilot/session-store.db
    → daily/YYYY-MM-DD.md logs
    → compile.py sends to Azure OpenAI / OpenAI
    → knowledge/concepts/, connections/, qa/
    → .github/copilot-instructions.md injects context into next session
    → cycle repeats
```

1. **Harvest** — Pulls your past Copilot CLI conversations from the local SQLite session store into structured daily log files.
2. **Compile** — An LLM reads each daily log and extracts knowledge into structured, cross-referenced wiki articles with YAML frontmatter and `[[wikilinks]]`.
3. **Query** — Ask questions against your knowledge base. The LLM reads the index, picks relevant articles, and synthesizes an answer with citations.
4. **Inject** — A `.github/copilot-instructions.md` file is auto-read by Copilot CLI at session start, pointing it to your compiled knowledge.

## Architecture

Three layers, following Karpathy's design:

| Layer | What It Is | Who Owns It |
|-------|-----------|-------------|
| **`daily/`** — Raw Sources | Conversation logs harvested from Copilot CLI. Immutable, append-only. | You (via harvest.py) |
| **`knowledge/`** — The Wiki | Structured, interlinked markdown articles. Concepts, connections, Q&A. | The LLM (via compile.py) |
| **`AGENTS.md`** — The Schema | Tells the LLM how the wiki is structured and what conventions to follow. | You + LLM (co-evolved) |

## Getting Started

### Prerequisites

- **GitHub Copilot CLI** — requires a [GitHub Copilot subscription](https://github.com/features/copilot) (Individual, Business, or Enterprise). You need existing session history in `~/.copilot/session-store.db`.
- **Azure OpenAI or OpenAI API key** — for compile, query, and lint operations (see [What You Need](#what-you-need))
- **Python 3.12+** — auto-managed by uv; you don't need to install it manually
- **[uv](https://docs.astral.sh/uv/)** — Python package manager (installed in setup below)

### Installation

1. **Clone the repo:**

    ```bash
    git clone https://github.com/AhmedChowdhury/copilot-memory-compiler.git
    cd copilot-memory-compiler
    ```

2. **Install dependencies:**

    ```bash
    # Install uv if you don't have it
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Install project dependencies
    uv sync
    ```

3. **Verify your session store exists:**

    ```bash
    ls ~/.copilot/session-store.db
    ```

    If this file exists, you have Copilot CLI conversation history ready to harvest.

### Configuration

1. **Copy the environment template:**

    ```bash
    cp .env.example .env
    ```

2. **Configure your LLM provider** (edit `.env`):

    **Option A — Azure OpenAI** (recommended if you have Azure access):

    ```env
    AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
    AZURE_OPENAI_API_KEY=your-key-here
    AZURE_OPENAI_DEPLOYMENT=gpt-4o
    AZURE_OPENAI_API_VERSION=2024-12-01-preview
    ```

    **Option B — OpenAI:**

    ```env
    OPENAI_API_KEY=sk-...
    LLM_MODEL=gpt-4o
    ```

## Usage

### Harvest Sessions

Pull conversations from your Copilot CLI session store into daily logs:

```bash
uv run python scripts/harvest.py              # harvest new sessions only
uv run python scripts/harvest.py --all         # re-harvest everything
uv run python scripts/harvest.py --dry-run     # preview what would be harvested
```

This reads `~/.copilot/session-store.db` in read-only mode and writes structured logs to `daily/`.

### Compile Knowledge

Compile daily logs into structured knowledge articles:

```bash
uv run python scripts/compile.py               # compile new/changed logs only
uv run python scripts/compile.py --all          # force recompile everything
uv run python scripts/compile.py --file daily/2026-04-15.md  # compile one log
uv run python scripts/compile.py --dry-run      # preview what would be compiled
```

The LLM reads each daily log and returns structured JSON. The script writes concept articles, connection articles, updates the index, and appends to the build log.

### Query the Knowledge Base

Ask questions and get answers grounded in your compiled knowledge:

```bash
uv run python scripts/query.py "What auth patterns do I use?"
uv run python scripts/query.py "How do I handle migrations?" --file-back
```

With `--file-back`, the answer is saved as a Q&A article in `knowledge/qa/` — so every question makes the knowledge base smarter.

### Lint (Health Checks)

Run 7 health checks on your knowledge base:

```bash
uv run python scripts/lint.py                    # all checks (including LLM)
uv run python scripts/lint.py --structural-only  # free structural checks only
```

Checks include: broken links, orphan pages, uncompiled sources, stale articles, missing backlinks, sparse articles, and cross-article contradictions.

### Full Pipeline

Run harvest + compile in one command:

```bash
./run.sh              # harvest new + compile changed
./run.sh --all        # re-harvest and recompile everything
./run.sh harvest      # harvest only
./run.sh compile      # compile only
```

## Why Not RAG?

This is Karpathy's key insight: at personal knowledge base scale (50–500 articles), the LLM reading a structured `index.md` **outperforms vector similarity search**. The LLM understands what you're really asking; cosine similarity just finds similar words.

| Approach | How It Works | Limitation |
|----------|-------------|------------|
| **RAG** | Chunk → embed → retrieve → generate. Knowledge re-derived every query. | No accumulation. No synthesis. No cross-referencing. |
| **Wiki Compiler** | Compile once → persistent wiki → index-guided retrieval. Knowledge compounds. | Needs recompilation when sources change. |

RAG becomes necessary at ~2,000+ articles when the index exceeds the context window. Until then, the structured index approach is simpler, cheaper, and more accurate.

## Project Structure

```
copilot-memory-compiler/
├── .github/
│   └── copilot-instructions.md   # Auto-injected into Copilot CLI sessions
├── daily/                         # "Source code" — conversation logs (immutable)
│   ├── 2026-04-15.md
│   └── 2026-04-16.md
├── knowledge/                     # "Executable" — compiled knowledge (LLM-owned)
│   ├── index.md                   #   Master catalog — THE retrieval mechanism
│   ├── log.md                     #   Append-only build log
│   ├── concepts/                  #   Atomic knowledge articles
│   ├── connections/               #   Cross-cutting insights linking 2+ concepts
│   └── qa/                        #   Filed query answers (compounding knowledge)
├── scripts/
│   ├── config.py                  #   Path constants and configuration
│   ├── llm.py                     #   LLM abstraction (Azure OpenAI / OpenAI)
│   ├── utils.py                   #   Shared helpers
│   ├── harvest.py                 #   Copilot CLI session store → daily logs
│   ├── compile.py                 #   Daily logs → knowledge articles
│   ├── query.py                   #   Ask questions against the knowledge base
│   └── lint.py                    #   7 health checks
├── hooks/                         # Claude Code hooks (not used with Copilot CLI)
├── AGENTS.md                      # Schema — full technical reference
├── run.sh                         # Pipeline script (harvest → compile)
├── pyproject.toml                 # Dependencies
├── .env.example                   # LLM provider config template
└── .gitignore
```

## How It Differs from the Claude Code Version

This project adapts [coleam00's Claude Code implementation](https://github.com/coleam00/claude-memory-compiler) for GitHub Copilot CLI:

| Feature | Claude Code Version | Copilot CLI Version |
|---------|-------------------|-------------------|
| **Session capture** | Hooks (SessionStart/End/PreCompact) | `harvest.py` reads `~/.copilot/session-store.db` |
| **LLM provider** | Claude Agent SDK (Anthropic) | OpenAI SDK (Azure OpenAI or OpenAI) |
| **Knowledge injection** | SessionStart hook injects context | `.github/copilot-instructions.md` auto-read |
| **Automation** | Hooks fire automatically | Manual `./run.sh` or cron job |
| **Compilation output** | LLM uses file tools directly | LLM returns JSON, script writes files |
| **Background flush** | `flush.py` spawned by hooks | Not needed — harvest pulls from session store |

The core architecture — daily logs → compile → wiki → inject — is identical. Only the integration points differ.

## Customization

### Timezone

Edit `scripts/config.py` to set your timezone:

```python
TIMEZONE = "America/New_York"  # Change to your timezone
```

### Additional Article Types

Add directories like `knowledge/people/`, `knowledge/projects/`, `knowledge/tools/`. Define the article format in `AGENTS.md` and update `utils.py`'s `list_wiki_articles()` to include them.

### Obsidian Integration

The knowledge base is pure markdown with `[[wikilinks]]` — it works natively in Obsidian. Point a vault at `knowledge/` for graph view, backlinks, and search.

### Scheduling with Cron

To automate the pipeline daily:

```bash
# Run harvest + compile every day at 7 PM
0 19 * * * cd /path/to/copilot-memory-compiler && ./run.sh >> /tmp/memory-compile.log 2>&1
```

## Costs

| Operation | Estimated Cost |
|-----------|---------------|
| Harvest (any amount) | $0.00 (local SQLite read) |
| Compile one daily log | ~$0.05–0.15 (depends on log size) |
| Query (no file-back) | ~$0.02–0.05 |
| Query (with file-back) | ~$0.03–0.08 |
| Structural lint | $0.00 |
| Full lint (with contradictions) | ~$0.02–0.05 |

Costs are for Azure OpenAI / OpenAI API usage. Harvest is always free — it only reads a local database.

## Contributing

This is a personal tool designed to be forked and customized. Feel free to fork it and adapt it to your workflow. If you build something interesting on top of it, I'd love to hear about it.

**Note:** This repo is not set up for upstream contributions. Fork it and make it your own.

## Credits

- **[Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)** — Original LLM Knowledge Base architecture
- **[coleam00](https://github.com/coleam00/claude-memory-compiler)** — Claude Code implementation that this project adapts

## License

[MIT](LICENSE)
