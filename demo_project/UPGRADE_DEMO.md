# MCP Server + AI Agent Upgrade Demo

Use this demo to show how the **Python Package MCP Server** guides dependency upgrades for a real application. The project intentionally mixes modern code with a history of legacy APIs so the agent can surface migration work.

## What This Demo Highlights

- Detecting upgrade opportunities with `analyze_project_dependencies` and `plan_dependency_upgrades`
- Explaining API breakage with `compare_package_versions` and `get_migration_resources`
- Showing real code that already uses the new OpenAI client (`OpenAI` class) and secure dependency pins
- Running in offline mode when no API key is available so the flow always works on stage

## Demo Workflow

1. **Install and run**:
   ```bash
   pip install -r requirements.txt
   python cli_app.py --use-sample --full-demo   # or add --offline for a keyless run
   ```
2. **Ask the agent to assess upgrades**:
   > "Scan this repo and propose an upgrade plan for its dependencies."

   The agent should call:
   - `analyze_project_dependencies()` to find declared requirements
   - `plan_dependency_upgrades()` to propose latest versions and risk levels
   - `get_package_metadata("openai")` to summarize the modern client API

3. **Explore breaking changes**:
   > "What changed between openai 0.27.8 and the latest release?"

   The agent will use `compare_package_versions()` to surface the shift from module-level configuration to the `OpenAI` client, new method paths, and updated response objects.

4. **Build a migration brief**:
   > "Generate a migration plan for moving from ChatCompletion.create to client.chat.completions.create in this project."

   The agent can pair `get_migration_resources()` with the local code to produce a checklist.

## Example Agent Outputs

- **Upgrade plan**: "openai (legacy pinned to 0.27.8) -> latest 1.52.0, risk: major (API surface changed); requests >=2.32.3 already current; click >=8.1.7 current."
- **Breaking change summary**: "Authentication is now client-based, chat/completions endpoints moved under client.chat/completions, embeddings under client.embeddings.create, moderation uses client.moderations.create; responses return typed models."
- **Code pointers**: "meeting_summarizer.py: replace module-level openai.* calls with client methods; ensure offline mode path remains intact."

## Tips for a Smooth Demo

- No API key? Use `--offline` and the local fallback keeps the experience interactive.
- Want to replay the legacy state? Pin `openai==0.27.8` in `requirements.txt` and rerun `plan_dependency_upgrades()` to show the contrast.
- Keep the MCP server logs visible; the structured tool calls make the upgrade flow easy to narrate.
