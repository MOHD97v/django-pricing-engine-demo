"""Seed three synthetic industries with realistic B2 configuration rules.

No production customer data, real orders, API keys, or private merchant assets.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalogue.models import Product, ProductClass
from apps.options.models import (
    OptionGroup, OptionChoice, OptionLevel, ProductClassOption,
    MarketIndex, PricingRule, RuleCondition,
)


class Command(BaseCommand):
    help = "Create/reset idempotent synthetic jewelry, fashion and food demo fixtures"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        # Only synthetic records in this isolated demo DB.
        def product_class(name):
            return ProductClass.objects.get_or_create(name=name)[0]

        def product(slug, title, description, kind, price, icon, accent):
            obj, _ = Product.objects.update_or_create(
                slug=slug, defaults={"title": title, "description": description,
                                     "product_class": kind, "base_price": Decimal(price),
                                     "icon": icon, "accent": accent})
            return obj

        def group(slug, name, name_ar, display, *, required=False, max_select=0,
                  uses_levels=False, order=0):
            obj, _ = OptionGroup.objects.update_or_create(
                slug=slug, defaults={"name": name, "name_ar": name_ar,
                                     "display": display, "is_required": required,
                                     "max_select": max_select, "uses_levels": uses_levels,
                                     "is_active": True, "sort_order": order})
            return obj

        def choice(grp, slug, name, name_ar, *, delta="0", default=False, color="",
                   default_qty=0, max_qty=0, deduct=False, order=0):
            obj, _ = OptionChoice.objects.update_or_create(
                group=grp, slug=slug, defaults={"name": name, "name_ar": name_ar,
                    "price_delta": Decimal(delta), "is_default": default,
                    "swatch_hex": color, "default_quantity": default_qty,
                    "max_quantity": max_qty, "deduct_below_default": deduct,
                    "is_active": True, "sort_order": order})
            return obj

        def level(grp, name, name_ar, *, is_none=False, default=False, order=0):
            obj, _ = OptionLevel.objects.update_or_create(
                group=grp, name_ar=name_ar, defaults={"name": name, "is_none": is_none,
                                                     "is_default": default, "sort_order": order})
            return obj

        def link(kind, grp, order):
            ProductClassOption.objects.update_or_create(
                product_class=kind, group=grp, defaults={"sort_order": order})

        def rule(name, name_ar, kind, *, adjustment, amount, product=None,
                 market=None, units="1", conditions=()):
            # Unique by name + product type for fixed synthetic fixture names.
            obj = PricingRule.objects.filter(name=name, applies_to_class=kind).first()
            values = {"name_ar": name_ar, "adjustment": adjustment,
                      "amount": Decimal(amount), "applies_to_product": product,
                      "market_index": market, "market_units": Decimal(units),
                      "is_active": True, "show_on_storefront": True,
                      "starts_on": None, "ends_on": None}
            if obj:
                for key, value in values.items():
                    setattr(obj, key, value)
                obj.save()
            else:
                obj = PricingRule.objects.create(name=name, applies_to_class=kind, **values)
            obj.conditions.all().delete()
            for selected_choice, selected_level in conditions:
                RuleCondition.objects.create(rule=obj, choice=selected_choice, level=selected_level)
            return obj

        jewelry = product_class("Jewelry")
        fashion = product_class("Fashion")
        food = product_class("Food")
        ring = product("studio-ring", "Studio Ring", "Configure metal, karat and finishing. Gold market rates are stored server-side.", jewelry, "250.00", "◇", "#9A785D")
        shirt = product("linen-shirt", "Linen Overshirt", "Select a size, color and optional personal embroidery.", fashion, "180.00", "▧", "#557F70")
        bowl = product("custom-bowl", "Custom Bowl", "Build a meal using a protein, add-ons, default-included quantities and spice levels.", food, "42.00", "◉", "#C18E5B")

        metal = group("metal", "Metal color", "لون المعدن", "swatch", required=True, max_select=1, order=1)
        choice(metal, "yellow", "Yellow gold", "ذهب أصفر", default=True, color="#C6A05E", order=1)
        choice(metal, "white", "White gold", "ذهب أبيض", color="#B8C4C5", order=2)
        choice(metal, "rose", "Rose gold", "ذهب وردي", color="#C78B82", order=3)
        karat = group("karat", "Gold purity", "عيار الذهب", "dropdown", required=True, max_select=1, order=2)
        k18 = choice(karat, "18k", "18K", "عيار 18", default=True, order=1)
        k21 = choice(karat, "21k", "21K", "عيار 21", order=2)
        finish = group("finish", "Optional finishing", "التشطيب الاختياري", "checkbox", order=3)
        choice(finish, "engraving", "Engraving", "نقش", delta="35", order=1)
        choice(finish, "gift-box", "Premium gift box", "علبة هدايا", delta="20", order=2)
        for i, grp in enumerate((metal, karat, finish), 1):
            link(jewelry, grp, i)
        gold, _ = MarketIndex.objects.update_or_create(
            code="gold-sar-g", defaults={"name": "Reference gold quote / gram",
                "name_ar": "سعر الذهب المرجعي لكل غرام", "provider": "manual",
                "current_value": Decimal("300.0000"), "currency": "SAR", "unit": "g",
                "is_active": True, "max_age_minutes": 180})
        rule("18K gold adjustment", "قيمة ذهب عيار 18", jewelry,
             adjustment="market", amount="0.750", units="3", market=gold,
             conditions=[(k18, None)])
        rule("21K gold adjustment", "قيمة ذهب عيار 21", jewelry,
             adjustment="market", amount="0.875", units="3", market=gold,
             conditions=[(k21, None)])

        size = group("apparel-size", "Size", "المقاس", "chips", required=True, max_select=1, order=1)
        choice(size, "small", "Small", "صغير", order=1)
        choice(size, "medium", "Medium", "متوسط", default=True, order=2)
        choice(size, "large", "Large", "كبير", order=3)
        color = group("apparel-color", "Color", "اللون", "swatch", required=True, max_select=1, order=2)
        choice(color, "sage", "Sage", "أخضر هادئ", default=True, color="#849A88", order=1)
        choice(color, "stone", "Stone", "حجري", color="#D6C7AF", order=2)
        choice(color, "charcoal", "Charcoal", "فحمي", color="#555A59", order=3)
        embellishment = group("embroidery", "Personalization", "تخصيص", "checkbox", order=3)
        embroidery = choice(embellishment, "monogram", "Monogram", "حروف مطرزة", delta="15", order=1)
        for i, grp in enumerate((size, color, embellishment), 1):
            link(fashion, grp, i)
        rule("Embroidery design premium", "رسوم تطريز إضافية", fashion,
             adjustment="percent", amount="5", conditions=[(embroidery, None)])

        protein = group("protein", "Protein", "البروتين", "radio", required=True, max_select=1, order=1)
        choice(protein, "chicken", "Chicken", "دجاج", default=True, order=1)
        choice(protein, "tofu", "Tofu", "توفو", order=2)
        choice(protein, "beef", "Beef", "لحم", delta="8", order=3)
        extras = group("toppings", "Ingredients & extras", "الإضافات", "stepper", order=2)
        choice(extras, "avocado", "Avocado (1 included)", "أفوكادو (واحد مشمول)",
               delta="6", default_qty=1, max_qty=4, deduct=True, order=1)
        choice(extras, "cheese", "Cheese", "جبن", delta="3", max_qty=5, order=2)
        heat = group("spice-level", "Spice level", "مستوى الحار", "levels", uses_levels=True, order=3)
        chili = choice(heat, "chili", "Chili", "شطة", default=True, order=1)
        level(heat, "None", "بدون", is_none=True, order=1)
        mild = level(heat, "Little", "قليل", default=True, order=2)
        extra = level(heat, "Extra", "زيادة", order=3)
        for i, grp in enumerate((protein, extras, heat), 1):
            link(food, grp, i)
        rule("Extra spice preparation", "إعداد الشطة الإضافية", food,
             adjustment="fixed", amount="4", conditions=[(chili, extra)])

        self.stdout.write(self.style.SUCCESS(
            "Seeded 3 synthetic products with shared B2 configuration + pricing rules.\n"
            "No real store data or API credentials were imported."))
