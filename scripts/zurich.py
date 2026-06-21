#!/usr/bin/env python3
"""Zurich/Petolo dog-insurance CLI — talks to the zurich-azure MCP server directly.

Why this exists: slow local models time out when forced to load 13 MCP tool
schemas and run a multi-round agentic loop. This script does the MCP JSON-RPC
handshake + tool call itself, so the model only has to run ONE command with
plain args and read plain text back. No tool schemas in context, no loop.

Usage (each command is one fast call):
  zurich.py breeds <term>
  zurich.py quote --breed NAME [--age N | --dob YYYY-MM-DD] [--name NAME]
  zurich.py start-dates
  zurich.py doc --breed NAME [--name NAME] [--dob YYYY-MM-DD] [--tier NAME]
  zurich.py preview --customer file.json      # dry-run: PREVIEW only, never binds
  zurich.py bind --customer file.json --yes-bind-real-money   # FINAL: spends money

The customer JSON (for preview/bind) holds: breed, tier, date_of_birth, dog_name,
dog_gender, first_name, last_name, owner_gender, owner_date_of_birth, email,
phone_number, iban, street_name, house_number, postcode, city, billing_day,
start_date. (billing_day is a STRING, e.g. "1".)
"""
import argparse, json, os, sys, urllib.request

SERVER = os.environ.get("ZURICH_MCP_SERVER", "zurich-azure")
DEFAULT_CONFIG = os.environ.get("OPENCLAW_CONFIG", os.path.expanduser("~/.openclaw/openclaw.json"))


def _server():
    """Resolve (url, headers) for the MCP server.

    1) Env override — portable, no OpenClaw needed:
         ZURICH_MCP_URL + ZURICH_MCP_API_KEY
    2) Fall back to the OpenClaw config (mcp.servers.<SERVER>), path from
       OPENCLAW_CONFIG or ~/.openclaw/openclaw.json.
    """
    url = os.environ.get("ZURICH_MCP_URL")
    key = os.environ.get("ZURICH_MCP_API_KEY")
    if url and key:
        return url, {"x-api-key": key}
    d = json.load(open(DEFAULT_CONFIG))["mcp"]["servers"][SERVER]
    return d["url"], d.get("headers", {})


def _post(url, headers, body, session=None):
    h = {"Content-Type": "application/json",
         "Accept": "application/json, text/event-stream", **headers}
    if session:
        h["mcp-session-id"] = session
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
    resp = urllib.request.urlopen(req, timeout=60)
    return resp.headers.get("mcp-session-id"), resp.read().decode()


def _parse_sse(text):
    """Pull the JSON object out of an SSE 'data: {...}' frame (or plain JSON)."""
    for line in text.splitlines():
        line = line[6:] if line.startswith("data: ") else line
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    raise RuntimeError(f"no JSON in response: {text[:300]}")


def call(tool, arguments):
    url, headers = _server()
    # handshake
    sid, _ = _post(url, headers, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                  "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                             "clientInfo": {"name": "zurich-cli", "version": "1"}}})
    _post(url, headers, {"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    # tool call
    _, body = _post(url, headers, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                   "params": {"name": tool, "arguments": arguments}}, sid)
    msg = _parse_sse(body)
    if "error" in msg:
        raise RuntimeError(msg["error"])
    text = msg["result"]["content"][0]["text"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}


def _print_quotes(o):
    print(f"Breed: {o.get('breed')}  DOB: {o.get('date_of_birth')} (assumed={o.get('dob_assumed')})")
    for q in o.get("quotes", []):
        print(f"  {q['tier']:<13} €{q['monthly_price_eur']}/month")


def main():
    p = argparse.ArgumentParser(prog="zurich.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("breeds"); s.add_argument("term")
    s = sub.add_parser("quote")
    s.add_argument("--breed", required=True); s.add_argument("--age", type=int)
    s.add_argument("--dob"); s.add_argument("--name")
    sub.add_parser("start-dates")
    s = sub.add_parser("doc")
    s.add_argument("--breed", required=True); s.add_argument("--name")
    s.add_argument("--dob"); s.add_argument("--tier")
    s = sub.add_parser("preview"); s.add_argument("--customer", required=True)
    s = sub.add_parser("bind"); s.add_argument("--customer", required=True)
    s.add_argument("--yes-bind-real-money", action="store_true")
    a = p.parse_args()

    if a.cmd == "breeds":
        o = call("search_breeds", {"term": a.term})
        for b in o.get("breeds", []):
            print(f"  id={b['id']}  {b['name']}")

    elif a.cmd == "quote":
        args = {"breed": a.breed}
        if a.age is not None: args["age_years"] = a.age
        if a.dob: args["date_of_birth"] = a.dob
        if a.name: args["dog_name"] = a.name
        if "age_years" not in args and "date_of_birth" not in args:
            sys.exit("error: provide --age or --dob")
        _print_quotes(call("get_quote", args))

    elif a.cmd == "start-dates":
        o = call("get_available_start_dates", {})
        print("Valid start dates:", ", ".join(o.get("available_start_dates", [])))

    elif a.cmd == "doc":
        args = {"breed": a.breed}
        if a.name: args["dog_name"] = a.name
        if a.dob: args["date_of_birth"] = a.dob
        if a.tier: args["recommended_tier"] = a.tier
        o = call("generate_quote_document", args)
        print(o.get("document_url") or o.get("text") or json.dumps(o))

    elif a.cmd in ("preview", "bind"):
        data = json.load(open(a.customer))
        data["dry_run"] = (a.cmd == "preview")
        if a.cmd == "bind":
            if not a.yes_bind_real_money:
                sys.exit("REFUSED: `bind` creates a paid contract. Re-run with "
                         "--yes-bind-real-money only after explicit customer confirmation.")
            data["ack"] = True
        o = call("complete_purchase", data)
        print(json.dumps(o, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
