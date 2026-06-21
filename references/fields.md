# Field reference — Petolo dog insurance

## Tiers (pass by NAME)
`Comfort` · `Premium` · `Premium Plus`. Use `get_available_policies()` for what
each covers. Prices come from `get_quote` / `get_price` — never quote from memory.

## Formats
- **Dates:** `YYYY-MM-DD`. Dog DOB: month+year is enough → assume the 1st (`"March 2022"` → `2022-03-01`).
- **Phone:** German, `+49…`.
- **IBAN:** German, `DE…`.
- **Postcode / city:** German.
- **Start date:** must be one returned by `get_available_start_dates()` (1st of a month, current month up to 6 months out). Do not invent one.
- **`billing_day`:** pass as a **string**, e.g. `"1"` (not the integer `1` — the server rejects an int).

## Unknown / mixed breeds
Resolve via `search_breeds(term)`. For mixes use the Petolo catch-alls by shoulder height:
- `Mischling Groß Schulterhöhe größer als 45 cm` — shoulder height **> 45 cm**
- `Mischling Klein Schulterhöhe bis einschließlich 45 cm` — **≤ 45 cm**

## `complete_purchase` parameters
Control: `dry_run` (bool — True = preview, False = bind), `ack` (bool — must be True to bind), `lead_uuid` (from the dry-run preview).

Dog: `breed`, `tier`, `date_of_birth`, `dog_name`, `dog_gender`.

Owner: `first_name`, `last_name`, `owner_gender`, `owner_date_of_birth`, `email`,
`phone_number`, `iban`, `billing_day`, `start_date`.

Address: `street_name`, `house_number`, `postcode`, `city`.

## Other tool args
- `get_quote(breed, date_of_birth, dog_name?, age_years?)`
- `get_price(breed_id*, policy_category*, date_of_birth*)` — needs a `breed_id` (from `search_breeds`); prefer `get_quote` which resolves it for you.
- `generate_quote_document(breed*, dog_name?, date_of_birth?, komfort_price?, premium_price?, premium_plus_price?, recommended_tier?)` → public HTML URL.
- `check_recurring_lead(uuid*, email*, phone_number*)` — detect an existing/duplicate lead before creating a new one.
- `bind_policy(confirmation_token*, idempotency_key*)` — low-level bind; `complete_purchase` is the normal path.
- `end_conversation(reason?, summary?, quote_accepted?, next_steps?)`

## Worked example
1. `search_breeds("Labrador")` → confirm breed name.
2. `get_quote(breed="Labrador Retriever", date_of_birth="2022-03-01", dog_name="Rex")` → three tier prices.
3. Customer picks **Premium**.
4. `complete_purchase(dry_run=True, breed="Labrador Retriever", tier="Premium", date_of_birth="2022-03-01", dog_name="Rex", first_name="…", last_name="…", email="…", phone_number="+49…", iban="DE…", postcode="…", city="…", street_name="…", house_number="…", start_date="2026-07-01", …)` → `lead_uuid`, `available_start_dates`.
5. **Show price + start date, get explicit "yes".**
6. `complete_purchase(dry_run=False, ack=True, lead_uuid="<uuid>", …same fields…)` → bound.
7. `end_conversation(reason="bound", quote_accepted=true, summary="Premium for Rex from 2026-07-01")`.
