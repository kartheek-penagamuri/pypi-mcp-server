# Python Package MCP Server (Hackathon Deck)

## Slide 1: The Problem and the Bet
AI coding systems stumble on Python packages:
- Knowledge cutoffs hide new releases and API shifts.
- Dependency context is siloed per file, not per project.
- PyPI discovery is noisy and slow for agents.
- Version conflicts surface late and break delivery.

**Bet:** A Model Context Protocol server that injects real-time, project-aware PyPI intelligence into every AI assistant.

## Slide 2: What We Ship Today
- `analyze_project_dependencies`: Multi-file dependency extraction with mtime refresh.
- `get_package_metadata`: Local-first metadata and README retrieval with PyPI fallback.
- `search_packages`: High-signal search with exact-name fallback.
- `check_package_compatibility`: Constraint intersection to catch conflicts early.
- `get_latest_version`: Latest non-yanked release with prerelease opt-in.
- `analyze_package_api_surface` and `compare_package_versions`: API surface diffs and migration signals.
- **New:** `plan_dependency_upgrades` builds an ordered upgrade plan with risk labels.

Tech stack: FastMCP server, httpx + BeautifulSoup, packaging, pytest, Python 3.10+.

## Slide 3: Impact and Story
- Closes the knowledge-cutoff gap with live PyPI data and local caches.
- Surfaces migration risk before coding begins.
- Turns READMEs and changelogs into usable context for agents.
- Demo-ready: Meeting Notes Summarizer upgraded to the OpenAI client SDK (v1.x) with offline mode for stage reliability.

## Slide 4: What's Next
- Retrieval-augmented slices of READMEs and changelogs scoped to the user's query.
- Golden-path evaluation harness with fixture projects and expected tool outputs.
- Pre-flight security insights (yanked releases, CVE feeds) in the upgrade planner.
