# Audit — zurich-dog-insurance skill & the slow-model work

> For human reviewers. This file lives in `docs/` and is **not** referenced by
> `SKILL.md`, so OpenClaw never loads it into the model context. Edit freely.

Date: 2026-06-21. Box: Mac mini, 16 GB unified memory, local Ollama only.

## 1. What the skill is
Wraps the **`zurich-azure`** MCP server (`ZurichInsuranceAdvisor` v1.27.2 — DA
Direkt / Petolo dog health insurance, German residents). Workflow: quote → lead
→ preview → bind. The server can create **paid, binding contracts**
(`bind_policy`, `complete_purchase(dry_run=False)`), so guardrails matter.

Registered with:
```
openclaw mcp add zurich-azure \
  --url https://zurich-mcp-server.ambitiousdesert-67d6610f.southeastasia.azurecontainerapps.io/mcp \
  --transport streamable-http --header x-api-key=<KEY> --timeout 60
```
Stored under `mcp.servers.zurich-azure` in `openclaw.json`. NOTE: the API key is
plaintext there and can bind contracts — treat as a secret / consider env-var.

## 2. Why the skill is script-based (not raw MCP tools)
Letting the local model (`gemma4-12b-32k`) drive the 13 MCP tools directly
**timed out** every time. Two costs on this hardware:
- Prefilling ~14.7k system prompt + 13 tool schemas (esp. `complete_purchase`,
  20 params) every turn.
- The multi-round agentic tool loop, each round re-prefilling the whole context.

Fix: `scripts/zurich.py` does the MCP JSON-RPC handshake + call itself. The model
runs ONE bash command (`python3 scripts/zurich.py quote --breed Chihuahua --age 10`)
and reads plain text (~3 s). The 13 tools are hidden from the model via
`openclaw mcp tools zurich-azure --exclude '*'` (saved as `toolFilter.exclude:["*"]`);
the script still reaches the server over HTTP directly. Guardrails live in the
script: `preview` = dry-run (never binds); `bind` refuses without
`--yes-bind-real-money`. Discovered in testing: `billing_day` must be a **string**.

## 3. The "73 native commands" — what they were
With `commands.native:"auto"` and `commands.nativeSkills:"auto"` (pre-trim
`commands` block: `{native:"auto", nativeSkills:"auto", restart:true}`), OpenClaw
injected a slash-command catalog into the system prompt and the Telegram menu
(the gateway log: "…to keep 73 commands visible"). The 73 ≈ two groups:

- **~40 built-in native commands** — verified examples: `/help /reset /new
  /compact /model /stop /status /think /fast /agents /approve /doctor /export
  /session /tts /usage /whoami` (plus more; the catalog is built at runtime as
  `menuCommandCatalog` in `dist/bot-*.js`).
- **32 skills surfaced as commands** — every enabled skill became a slash command
  via `nativeSkills:"auto"` (see §4 for the list).

Built-in + skills-as-commands ≈ 73. To regenerate the exact live list: set
`commands.native:"auto"`, restart the gateway, then
`curl …/getMyCommands` (Telegram) or check the menu.

## 4. System-prompt trim (the speed fix the user chose)
Backup before changes: `openclaw.json.bak.pretrim`.

- **`commands.native: false`** — removes the ~40 built-in slash commands from the
  prompt. Tradeoff: the model no longer advertises/uses built-in `/commands`.
- **Skills 32 → 4** — kept `zurich-dog-insurance`, `browser`, `healthcheck`
  (+1). Disabled 28: `1password blogwatcher camsnap canvas clawhub diagram-maker
  gemini gh-issues github gog himalaya imsg mcporter meme-maker node-connect
  node-inspect-debugger openai-whisper peekaboo python-debugpy skill-creator
  spike summarize taskflow taskflow-inbox-triage things-mac video-frames wacli
  weather`.

Revert any of it:
```
cp openclaw.json.bak.pretrim openclaw.json      # full revert
# or granularly:
openclaw skills enable <name>
# set commands.native back to "auto" in openclaw.json
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway   # apply
```

## 5. Performance findings (measured)
- Warm model, small prompt: **1.0 s**. Model is fine when context is small.
- Warm model, ~15 k-token prompt: **124 s prefill** (`prompt_eval=15025`) before
  the first token. This is the real wall, and it is the BASE system prompt — not
  the skill.
- OpenClaw idle timeout: `DEFAULT_LLM_IDLE_TIMEOUT_MS = 120 s` → killed every run
  4 s short of first token.
- Fixes: `models.providers.ollama.timeoutSeconds: 600` — **requires a full
  gateway restart** (`launchctl kickstart -k`); hot-reload silently no-ops the
  provider runtime. Also: don't run `openclaw mcp reload` mid-turn — it restarts
  the gateway and kills the in-flight agent run (caused several false-negative
  tests here).
- First successful end-to-end run via ollama: **277 s** (correct prices:
  Comfort €56.90 / Premium €67.90 / Premium Plus €100.90). 277 s ≈ TWO prefills
  (decide-to-run-script, then read-result-and-answer); Ollama prefix KV-cache
  reuse did not span the two calls.
- After the §4 trim: **NO improvement.** Two post-trim runs of the same query:
  585 s (hit the run timeout) and 634 s (failed: "CLI transcript compaction timed
  out") — both WORSE than the 277 s baseline. Conclusion: turn time is dominated
  by the *number* of agentic round-trips (each re-prefilling ~12 k tokens), which
  varies run-to-run; shrinking the prompt ~20% did not reduce the round count and
  the extra failure mode (compaction) made it worse. The trim is reversible
  (`openclaw.json.bak.pretrim`) and did not buy speed — keep it only if the
  disabled skills/commands were unwanted anyway.
- **Verdict:** the local 12B on 16 GB can produce CORRECT answers through this
  skill but is too slow/unreliable for interactive agentic use (~5–10 min/turn,
  intermittent timeouts). For reliable/snappy use, route the agent at a faster
  model (cloud Anthropic profile already in config) and keep the 12B for async
  crons. The script-based skill design is correct and unaffected by that choice.

## 6. Remaining levers if still too slow
- Disable `nativeSkills` too (more prompt savings; small risk to skill triggering
  — test it).
- The bulk of the remaining ~12 k tokens is core agent instructions + tool
  schemas (Bash/Read/Edit) — not trimmable without breaking the agent.
- For genuinely snappy interactive chat: a smaller chat model, or route this
  agent to a fast cloud model (an Anthropic auth profile exists in config).

## Related
Memory notes (host-side, not in repo): `local-model-gemma4-12b`,
`gateway-watchdog`, `zurich-dog-insurance-skill`.
