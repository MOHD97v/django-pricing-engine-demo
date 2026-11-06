# Verification report

**Preparation date:** 6 November 2026  
**Source used:** Current `Modomutiorga/B2-Store` `main` pricing module and related data models, reviewed read-only.

## Checks performed in the generation environment

| Check | Status | Notes |
|---|---|---|
| Source inspection | PASS | Original pricing function, model fields, market staleness checks and payload shapes inspected in GitHub. |
| Python syntax compilation | PASS | `python -m compileall` over the complete standalone source tree. |
| JavaScript syntax check | PASS | `node --check apps/demo/static/demo/app.js`. |
| Browser UI/layout preview | PASS (mocked API) | Chromium rendered desktop (1440px) and mobile (390px) with synthetic intercepted API replies, with no browser errors or horizontal overflow. All three tabs and snapshot UI were exercised. This is **not** a live Django integration test. |
| Static secret/credential scan | PASS | No production keys, .env files, customer records or payment gateway credentials inserted. Local development key is clearly marked as nonproduction. |
| ZIP manifest | PASS | Source, tests, README, static assets and preview images included; no `.git`, database, or virtual environment. |
| Django integration/runtime tests | **NOT EXECUTED HERE** | Django package unavailable in the sandbox; installing it from PyPI failed due to network DNS restrictions. |
| Django `manage.py check`, migrations, seed and live browser | **NOT EXECUTED HERE** | Same dependency limitation. The repository includes instructions and tests for local verification. |

## Included automated test cases

The test suite in `apps/demo/tests.py` contains validation of:

1. Homepage and three seeded products.
2. 18K gold market-rate arithmetic and VAT.
3. Alternate 21K rule, without charging the 18K rule again.
4. Missing required choices.
5. Non-existent and foreign-product choices.
6. Maximum selections per group.
7. Included default quantity without double charging.
8. Opt-in negative stepper credit at zero quantity.
9. Stepper maximum quantity.
10. Food pricing with conditional levels and repeated quantities.
11. Invalid option level rejection.
12. Fashion fixed and conditional percentage adjustments.
13. Unavailable and stale market-rate rejection.
14. Client-submitted price spoofing ignored.
15. Invalid JSON rejection.
16. Negative total rejection.
17. Frozen historical snapshot remains unchanged after price changes.
18. CSRF rejection when token is absent.

## Before publication

On your own computer, run:

```bash
python -m pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py seed_demo
python manage.py check
python manage.py test apps.demo -v 2
python manage.py runserver
```

After it loads, manually verify product-switching, live price updates, and snapshot creation. If any test fails, **do not describe the demo as tested/passing** until resolved. This report does not claim a Django run passed.
