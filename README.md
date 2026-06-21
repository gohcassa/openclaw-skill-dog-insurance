# OpenClaw Skill — Zurich / DA Direkt (Petolo) Dog Insurance

Quote, document, and bind Petolo dog health insurance (German residents) from an
OpenClaw agent. It talks to the `ZurichInsuranceAdvisor` MCP server through a thin
script (`scripts/zurich.py`), so even small/slow local models can use it — the
model runs one command and reads plain text instead of driving 13 MCP tools.

> **The API key is never stored in this repo.** You supply it once at install
> time (env var or `openclaw mcp add`); it lives only in your local config.

## Install

1. Clone into your OpenClaw skills directory:
   ```bash
   git clone git@github.com:mahmalsami/openclaw-skill-dog-insurance.git \
     ~/.openclaw/workspace/skills/zurich-dog-insurance
   ```

2. Register the MCP server with **your** key (do not commit it):
   ```bash
   export ZURICH_MCP_API_KEY="<your-key>"
   openclaw mcp add zurich-azure \
     --url https://zurich-mcp-server.ambitiousdesert-67d6610f.southeastasia.azurecontainerapps.io/mcp \
     --transport streamable-http \
     --header x-api-key=$ZURICH_MCP_API_KEY \
     --timeout 60
   # optional: hide the raw tools from the model so the lean script path is used
   openclaw mcp tools zurich-azure --exclude '*'
   openclaw mcp reload
   ```
   (See `assets/mcp-server.example.json` for the equivalent config block.)

## How OpenClaw consumes it

`SKILL.md` instructs the agent to run `scripts/zurich.py <command>`. The script
resolves the server in this order:

1. Env vars `ZURICH_MCP_URL` + `ZURICH_MCP_API_KEY` (fully portable, no config), or
2. Your OpenClaw config `mcp.servers.zurich-azure` (after `openclaw mcp add`).

So once the server is registered (or the env vars are set), the skill just works.

## Use

```bash
python3 scripts/zurich.py breeds "Labrador"
python3 scripts/zurich.py quote --breed Chihuahua --age 10 --name Bella
python3 scripts/zurich.py start-dates
python3 scripts/zurich.py doc --breed Chihuahua --name Bella
```

Buying is two guarded steps (never skip the preview):
```bash
python3 scripts/zurich.py preview --customer customer.json                     # dry-run, never binds
python3 scripts/zurich.py bind    --customer customer.json --yes-bind-real-money  # FINAL: paid contract
```
Fill `customer.json` from `assets/customer.template.json`. `bind` refuses without
`--yes-bind-real-money`.

## Security

- **No secrets in this repo.** The key is provided via env var or `openclaw mcp
  add` and stored only in your local `openclaw.json`.
- `complete_purchase(dry_run=False)` / `bind` create **paid, binding contracts** —
  always `preview` and get explicit customer confirmation first.

## Layout

| Path | Purpose |
|---|---|
| `SKILL.md` | Agent-facing workflow (loads into context on trigger) |
| `scripts/zurich.py` | MCP CLI — does the JSON-RPC handshake + calls |
| `references/fields.md` | Field formats, tiers, breed catch-alls |
| `assets/customer.template.json` | Fill-in form for purchases |
| `assets/mcp-server.example.json` | Server config block (no key) |
| `docs/audit.md` | Design + performance notes (not loaded into context) |
