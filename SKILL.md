---
name: zurich-dog-insurance
description: "Quote and bind Zurich / DA Direkt (Petolo) dog health insurance for German residents. Run the scripts/zurich.py commands — they call the zurich-azure MCP server directly."
metadata:
  type: workflow
  mcp-server: zurich-azure
---

# Zurich Dog Insurance

Quote, document, and bind Petolo dog health insurance. **Do not call MCP tools
directly** — run `python3 scripts/zurich.py <command>`. Each command is one fast
call (~3s) and prints plain text, so even a small/slow model just runs a command
and reads the result. German residents only (phone `+49…`, IBAN `DE…`).

## Quote (the common case)

```
python3 scripts/zurich.py quote --breed "Chihuahua" --age 10 --name Bella
```
- Pass `--age N` OR `--dob YYYY-MM-DD` (month+year is fine; a known age is fine).
- Unknown/mixed breed first: `python3 scripts/zurich.py breeds "<term>"` to find the exact name (mixed dogs → search `Mischling`).
- always generate shareable quote doc: `python3 scripts/zurich.py doc --breed "Chihuahua" --name Bella`.

Show the three tier prices (Comfort / Premium / Premium Plus) and stop unless the
customer wants to buy.

## Buy (two steps — never skip step 1)

1. Fill a customer file from `assets/customer.template.json` (all fields; `billing_day` is a string; `start_date` must come from `python3 scripts/zurich.py start-dates`). Then **preview**:
   ```
   python3 scripts/zurich.py preview --customer /tmp/customer.json
   ```
   This is a dry run — it returns a `lead_uuid`, price, and start date but does **not** bind. Show these to the customer and get an explicit "yes".

2. Only after that yes, **bind** (this spends real money / creates a contract):
   ```
   python3 scripts/zurich.py bind --customer /tmp/customer.json --yes-bind-real-money
   ```
   The script refuses to bind without that flag. Never add it yourself without the customer's confirmation.

## Notes

- Field formats, tier table, and breed catch-alls: `references/fields.md`.
- If a command errors or the server workflow seems to have changed, the script is a thin wrapper over the `zurich-azure` MCP tools — re-probe with `openclaw mcp probe zurich-azure`.
