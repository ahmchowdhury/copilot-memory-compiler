# Personal Knowledge Base — Copilot CLI Memory System

This project maintains a personal knowledge base compiled from your Copilot CLI conversations.

## How it works
- Your past conversations are harvested from the Copilot CLI session store
- Daily logs are compiled into structured knowledge articles via LLM
- Knowledge lives in `knowledge/` as markdown with `[[wikilinks]]`

## For context on past work
- Read `knowledge/index.md` for a catalog of all compiled knowledge
- Browse `knowledge/concepts/` for atomic knowledge articles
- Browse `knowledge/connections/` for cross-cutting insights
- Browse `daily/` for raw conversation logs by date

## Schema reference
- See `AGENTS.md` for the full technical spec on article formats and conventions
