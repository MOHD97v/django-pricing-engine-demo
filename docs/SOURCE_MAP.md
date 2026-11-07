# Source map · Django pricing-engine demo

**Scope:** This public repository demonstrates the pricing rules and a minimal Django interface; it is **not** the full commerce system.

**Primary source (read-only):** `Modomutiorga/B2-Store`, branch `main`, reviewed 6 November 2026.

The private source backend is a larger Django/Django Oscar system. This public sample is not a drop-in copy of the original shop and is not the deployed Yagarz platform. All fixture products, prices, and item names here are **synthetic demonstration data**.

| Pricing-demo component | Relationship to the original |
|---|---|
| `apps/options/pricing.py` | Preserves the real `compute_price()` calculation logic and its option validation, stepper default/credit semantics, market freshness checks, conditional rules, and negative-total rejection. Formatting/comments are condensed for this isolated extract. Source: `apps/options/pricing.py`, Git blob SHA `dd856e0b6703249b8c946d42c1e5793cfb8d28a7`. |
| `apps/options/models.py` | Smaller compatible adaptation of the original `OptionGroup`, `OptionChoice`, `OptionLevel`, `ProductClassOption`, `MarketIndex`, `PricingRule`, `RuleCondition`. Removes unused media uploads, API credentials/provider management, and Oscar-specific models. |
| `apps/catalogue/models.py` | Minimal Oscar-compatible `Product` and `ProductClass` stand-ins, including `get_product_class()`. **These are demo models, not the original Oscar models.** |
| `apps/demo/views.py` | New demonstration-only JSON endpoints, CSRF-protected quote POST, and a snapshot-save endpoint. All price calculations delegate to the real `compute_price()` implementation. |
| `apps/demo/models.py` | New demonstration-only JSON snapshot table; illustrates price immutability, not the original checkout/order persistence wiring. The original uses `apps/options/order_snapshot.py`. |
| `apps/demo/management/commands/seed_demo.py` | New synthetic fixtures for jewelry, fashion, food; seeded market rate is made up for demonstration. |
| `apps/demo/static/demo/` and templates | New public interface, not an imported piece of the production Yagarz storefront. |

## Deliberate omissions

The following are present in the full private B2 backend but not in this focused extract:

- Django Oscar's entire catalogue/basket/checkout/payment/shipping stack.
- The original order snapshot adapter to Oscar and its PDF invoice/transaction flows.
- External market API credentials, provider refresh jobs, and real data sources. The source-backed `_market_value()` still rejects unavailable or stale rates, and demo fixture rates are stored in SQLite.
- Merchant administration, localization templates across the full shop, video management, user/customer accounts, and product media uploads.

**Why:** This project is an independently reviewable, minimal demonstration of the original domain model and pricing authority, not a second full e-commerce business.

## Correct claims

- ✅ Uses actual backend calculation rules—not JavaScript simulation.
- ✅ Reuses the original engine's query logic, required/max-choice validation, level selection checks, stepper credits, market and conditional adjustments.
- ✅ Shows end-to-end Django GET/POST routes, server-side validation and persisted local sample snapshots.
- ✅ Offers synthetic jewelry/fashion/food configurations.
- ❌ Does not run Oscar itself, connect to the private production backend or Yagarz, call payment gateways, or pull live precious-metal feeds.
- ❌ Is not a production-ready deployment, and does not contain real customer data.
