# MOHD Configurable Commerce Engine · Django Engineering Demo

**One reusable customization and pricing engine. Three industries. Real server-side calculations.**

A focused, runnable demonstration of engineering work from a larger private Django/Django Oscar commerce backend. The important part is genuine: the pricing function used here follows the original backend's `compute_price()` logic, backed by adapted ORM models and synthetic configuration data. The website submits selections to Django; **it does not calculate prices in JavaScript**.

> **Scope:** Standalone local demo—not the original full Django Oscar store, no actual orders or payments, no production data, and no external credentials. See [`docs/SOURCE_MAP.md`](docs/SOURCE_MAP.md) for an exact breakdown of reused vs adapted vs demonstration-only code.

![UI example](screenshots/desktop.png)

## Start locally (Windows / macOS / Linux)

Prerequisite: **Python 3.12+** and internet access once to install Django. SQLite ships with Python; no PostgreSQL, Oscar, API keys or account required.

```bash
# Open a terminal in this repository folder
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell instead
# .venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py seed_demo
python manage.py runserver
```

Then open **http://127.0.0.1:8000/**.

On Windows, if `python` is unavailable, try `py -3.12` for the initial venv command. You do not need to set up an external database.

If your terminal uses a restricted PowerShell execution policy, you can skip activation and run commands with `.venv\Scripts\python.exe` directly.

## Try the three scenarios

| Scenario | Test | Actual backend behavior |
|---|---|---|
| **Jewelry** | Switch 18K ↔ 21K, add engraving | Only the matching market rule applies; option deltas and VAT are itemized. Gold values are local sample rates, **not live quotes**. |
| **Fashion** | Select size/color and turn on embroidery | Merchant configured choice adjustment (15 SAR) + conditional rule (5% of base price) are computed server-side. |
| **Food** | Increase/decrease included avocado, add cheese, choose extra chili | A default-included stepper is not double billed; optional deductions below the default and conditional level rules apply. |

Click **“Freeze this quote”** to save a demonstration-only JSON snapshot to the local SQLite database. The response freezes choice labels, quantities, adjustment rows and final amounts. It does **not** place a purchase order, charge money or contact a customer.

## Run the automated tests

```bash
python manage.py test apps.demo -v 2
python manage.py check
```

The tests cover required selections, maximum choices, cross-product invalid selections, stepper credits and limits, conditional gold/fashion/food pricing, market-rate availability and staleness, ignored client price tampering, VAT, negative final-price rejection, CSRF protection and historical snapshots.

**Verified locally:** Python 3.12 + Django 6.1.3 on Windows — **19 tests passed successfully**. Django's system check reported no issues during the test run.

## Architecture

```text
Synthetic Product Types and Product Configurations (SQLite)
                           |
                           v
        GET /api/products/{slug}/  -> option groups
                           |
                    Browser selection
                           |
                           v
             POST /api/quote/  (CSRF)
                           |
                Validate input/IDs
                           |
                           v
        apps/options/pricing.py::compute_price()
       (required choices, levels, stepper defaults,
          market-based/fixed/percent rules)
                           |
                           v
                Authoritative quote + VAT
                           |
                Optional user action
                           |
                           v
             POST /api/snapshots/
                           |
                           v
          Frozen DEMO record in SQLite
```

Core files:

- `apps/options/pricing.py` — pricing authority and business-rule evaluator.
- `apps/options/models.py` — compact version of the real reusable configuration model.
- `apps/catalogue/models.py` — minimal Oscar-compatible product and product-type stubs.
- `apps/demo/views.py` — public demo routes and saved snapshot flow.
- `apps/demo/management/commands/seed_demo.py` — three synthetic demonstrations.
- `apps/demo/tests.py` — actual Django tests (requires installing dependencies).

## The engineering point

A single configurable product platform can interpret different product selection mechanisms and pricing behaviors without creating separate code paths for every merchant industry. Configuration lives in the database; the backend resolves actual rules and validates the final amount. This is the same design principle used in the original private commerce platform.

## Local demo and security boundaries

- The example is intended to run on **your computer at 127.0.0.1**.
- `DEBUG=True` and the documented development key are for local development **only**. They are intentionally not production secrets. Do not deploy to the public internet without a new configuration and security review.
- No payment gateway, email account, OAuth client, customer account, production token, provider key, or personal records are included.
- POST routes use Django's default CSRF protection. Saved snapshots have no customer identity fields.
- The `demo.sqlite3` file is local and excluded via `.gitignore`.
- This small demo intentionally uses `migrate --run-syncdb` rather than importing the private store's migrations or full Oscar dependencies. The original backend has its own migrations. Do not treat this as a deployment architecture.
- All seeded products, prices and market quotes are **examples**, not Yagarz/ShipMatrix production values.

## Repository scope

This public repository is intentionally isolated from the original private commerce backend. Leave `demo.sqlite3`, `.venv` and `.env` out of commits (already covered by `.gitignore`).

Screenshots are UI previews; executable behavior requires running the Django server as described above.
