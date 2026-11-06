"""Public demonstration tests; require a working Django installation.

Run: python manage.py test apps.demo -v 2
All fixtures are synthetic; test DB is created automatically.
"""
import json
from decimal import Decimal
from datetime import timedelta

from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone

from apps.catalogue.models import Product
from apps.options.models import OptionChoice, MarketIndex, PricingRule
from apps.options.pricing import OptionError, compute_price
from .models import DemoOrderSnapshot


class ConfigurableCommerceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        cls.ring = Product.objects.get(slug="studio-ring")
        cls.shirt = Product.objects.get(slug="linen-shirt")
        cls.bowl = Product.objects.get(slug="custom-bowl")

    def settings_for(self, product):
        return self.client.get(f"/api/products/{product.slug}/").json()

    def send(self, product, selections, *, url="/api/quote/", extra=None):
        payload = {"product_slug": product.slug, "selections": selections}
        if extra:
            payload.update(extra)
        return self.client.post(url, data=json.dumps(payload), content_type="application/json")

    def choice(self, slug):
        return OptionChoice.objects.get(slug=slug)

    def test_homepage_and_three_examples(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        products = self.client.get("/api/products/").json()["products"]
        self.assertEqual(len(products), 3)
        self.assertEqual({p["category"] for p in products}, {"Jewelry", "Fashion", "Food"})

    def test_ring_uses_real_market_rule_and_vat(self):
        result = self.send(self.ring, self.settings_for(self.ring)["defaults"])
        self.assertEqual(result.status_code, 200)
        quote = result.json()
        self.assertEqual(quote["base"], "250.00")
        self.assertEqual(quote["subtotal"], "925.00")
        self.assertEqual(quote["vat"], "138.75")
        self.assertEqual(quote["total"], "1063.75")
        self.assertTrue(any(line["kind"] == "rule" and line["adjustment"] == "market" for line in quote["adjustments"]))

    def test_gold_21k_applies_alternative_rule_not_both(self):
        selections = self.settings_for(self.ring)["defaults"]
        selections.pop(str(self.choice("18k").id))
        selections[str(self.choice("21k").id)] = {"qty": 1, "level": None}
        resp = self.send(self.ring, selections)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["subtotal"], "1037.50")
        self.assertEqual(len([line for line in resp.json()["adjustments"] if line["kind"] == "rule"]), 1)

    def test_required_option_cannot_be_missing(self):
        resp = self.send(self.ring, {})
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["type"], "InvalidOptionSelection")

    def test_invalid_or_foreign_product_choice_rejected(self):
        resp = self.send(self.ring, {"9999999": {"qty": 1}})
        self.assertEqual(resp.status_code, 422)
        defaults = self.settings_for(self.ring)["defaults"]
        defaults[str(self.choice("medium").id)] = {"qty": 1}
        self.assertEqual(self.send(self.ring, defaults).status_code, 422)

    def test_max_select_is_server_enforced(self):
        defaults = self.settings_for(self.ring)["defaults"]
        defaults[str(self.choice("white").id)] = {"qty": 1}
        self.assertEqual(self.send(self.ring, defaults).status_code, 422)

    def test_food_default_included_stepper_not_double_charged(self):
        resp = self.send(self.bowl, self.settings_for(self.bowl)["defaults"])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["subtotal"], "42.00")
        self.assertEqual(resp.json()["total"], "48.30")

    def test_stepper_zero_quantity_returns_opt_in_credit(self):
        defaults = self.settings_for(self.bowl)["defaults"]
        defaults[str(self.choice("avocado").id)]["qty"] = 0
        resp = self.send(self.bowl, defaults)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["subtotal"], "36.00")
        self.assertTrue(any(Decimal(line["amount"]) == Decimal("-6.00") for line in resp.json()["adjustments"]))

    def test_stepper_quantity_limit(self):
        defaults = self.settings_for(self.bowl)["defaults"]
        defaults[str(self.choice("avocado").id)]["qty"] = 5
        self.assertEqual(self.send(self.bowl, defaults).status_code, 422)

    def test_food_level_and_quantity_rules(self):
        defaults = self.settings_for(self.bowl)["defaults"]
        cheese = self.choice("cheese")
        defaults[str(cheese.id)]["qty"] = 2
        current = self.choice("chili")
        level = current.group.levels.get(name="Extra")
        defaults[str(current.id)]["level"] = level.id
        defaults.pop(str(self.choice("chicken").id))
        defaults[str(self.choice("beef").id)] = {"level": None, "qty": 1}
        resp = self.send(self.bowl, defaults)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["subtotal"], "60.00")
        self.assertEqual(resp.json()["total"], "69.00")

    def test_wrong_level_id_rejected(self):
        defaults = self.settings_for(self.bowl)["defaults"]
        defaults[str(self.choice("chili").id)]["level"] = 999999
        self.assertEqual(self.send(self.bowl, defaults).status_code, 422)

    def test_fashion_percent_and_fixed_choice(self):
        defaults = self.settings_for(self.shirt)["defaults"]
        defaults[str(self.choice("monogram").id)] = {"level": None, "qty": 1}
        resp = self.send(self.shirt, defaults)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["subtotal"], "204.00")  # 180 + 15 + 5% of base (9)
        self.assertEqual(resp.json()["total"], "234.60")

    def test_unavailable_market_rate_fails_closed(self):
        market = MarketIndex.objects.get(code="gold-sar-g")
        market.current_value = None
        market.save(update_fields=["current_value"])
        self.assertEqual(self.send(self.ring, self.settings_for(self.ring)["defaults"]).status_code, 422)

    def test_stale_external_market_rate_fails_closed(self):
        market = MarketIndex.objects.get(code="gold-sar-g")
        market.provider = "metals_dev"
        market.last_updated = timezone.now() - timedelta(days=3)
        market.save(update_fields=["provider", "last_updated"])
        resp = self.send(self.ring, self.settings_for(self.ring)["defaults"])
        self.assertEqual(resp.status_code, 422)
        self.assertIn("stale", resp.json()["error"])

    def test_client_supplied_price_is_ignored(self):
        defaults = self.settings_for(self.ring)["defaults"]
        resp = self.send(self.ring, defaults, extra={"total": "0.01", "base": "0.01", "vat": "0"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["total"], "1063.75")

    def test_malformed_json_rejected(self):
        result = self.client.post("/api/quote/", data="{not json", content_type="application/json")
        self.assertEqual(result.status_code, 400)

    def test_negative_final_price_rejected(self):
        PricingRule.objects.create(name="Invalid huge credit", name_ar="خصم غير صالح", applies_to_class=self.bowl.product_class, adjustment="fixed", amount=Decimal("-9999"))
        self.assertEqual(self.send(self.bowl, self.settings_for(self.bowl)["defaults"]).status_code, 422)

    def test_snapshot_frozen_after_product_and_market_change(self):
        defaults = self.settings_for(self.ring)["defaults"]
        resp = self.send(self.ring, defaults, url="/api/snapshots/")
        self.assertEqual(resp.status_code, 201)
        identifier = resp.json()["id"]
        frozen = resp.json()["snapshot"]
        self.assertTrue(frozen["demo_only"])
        self.assertEqual(frozen["pricing"]["total"], "1063.75")
        self.assertTrue(frozen["selected_options"])
        self.ring.base_price = Decimal("1000.00")
        self.ring.save(update_fields=["base_price"])
        market = MarketIndex.objects.get(code="gold-sar-g")
        market.current_value = Decimal("900.0000")
        market.save(update_fields=["current_value"])
        retrieved = self.client.get(f"/api/snapshots/{identifier}/")
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(retrieved.json()["snapshot"], frozen)
        self.assertEqual(DemoOrderSnapshot.objects.count(), 1)
        self.assertNotEqual(self.send(self.ring, defaults).json()["total"], frozen["pricing"]["total"])

    def test_post_csrf_protected_in_real_browser(self):
        csrf_client = Client(enforce_csrf_checks=True)
        page = csrf_client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("csrftoken", page.cookies)
        resp = csrf_client.post("/api/quote/", data=json.dumps({"product_slug": self.ring.slug, "selections": {}}), content_type="application/json")
        self.assertEqual(resp.status_code, 403)
