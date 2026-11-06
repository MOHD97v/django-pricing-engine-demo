"""B2 Store pricing authority — logic preserved from the real backend.

Source: Modomutiorga/B2-Store/apps/options/pricing.py
Original blob SHA: dd856e0b6703249b8c946d42c1e5793cfb8d28a7

The function below follows the original implementation and selection semantics.
The standalone demo supplies minimal compatible Django models in place of
Oscar's Product/ProductClass. No fake formula replaces the real engine.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone, translation

from .models import OptionChoice, OptionLevel, PricingRule, ProductClassOption

CENT = Decimal("0.01")


class OptionError(Exception):
    def __init__(self, ar, en):
        super().__init__(en)
        self.ar = ar
        self.en = en

    def message(self):
        language = translation.get_language() or ""
        if language.startswith("en"):
            return self.en
        return self.ar


class InvalidOptionSelection(OptionError):
    """A saved selection no longer matches the merchant's current options.

    Distinct from transient market-data failures: only this error may cause
    an outdated OPEN basket line to be removed automatically.
    """


def _selection_parts(value):
    """New {level, qty} and legacy level-only selections are supported."""
    if isinstance(value, dict):
        level_id = value.get("level")
        try:
            quantity = int(value.get("qty", 1))
        except (TypeError, ValueError):
            quantity = 1
    else:
        level_id = value
        quantity = 1
    if quantity < 0:
        quantity = 0
    return level_id, quantity


def _market_value(index):
    if index is None or not index.is_active or index.current_value is None:
        raise OptionError("سعر السوق غير متاح حالياً", "The market price is currently unavailable")

    if index.provider != "manual" and index.max_age_minutes:
        if not index.last_updated:
            raise OptionError("لم يتم تحديث سعر السوق بعد", "The market price has not been updated yet")
        oldest_allowed = timezone.now() - timedelta(minutes=index.max_age_minutes)
        if index.last_updated < oldest_allowed:
            raise OptionError("سعر السوق قديم ويحتاج إلى تحديث", "The market price is stale and must be refreshed")
    return index.current_value


def compute_price(product, base_price, selections):
    """Authoritative B2 price computation, using actual persisted configurations.

    Selections: {choice_id: {"level": level_id|None, "qty": int}}.
    Original legacy {choice_id: level_id} is also supported.
    """
    pclass = product.get_product_class()
    groups = {
        link.group_id: link.group
        for link in ProductClassOption.objects.filter(
            product_class=pclass, group__is_active=True,
        ).select_related("group")
    }
    choices = {
        choice.id: choice
        for choice in OptionChoice.objects.filter(
            id__in=list(selections), is_active=True,
        ).select_related("group")
    }
    requested_level_ids = []
    for value in selections.values():
        level_id, quantity = _selection_parts(value)
        if level_id:
            requested_level_ids.append(level_id)
    levels = {
        level.id: level
        for level in OptionLevel.objects.filter(id__in=requested_level_ids)
    }
    active = {}
    for choice_id, raw_selection in selections.items():
        choice = choices.get(choice_id)
        if choice is None or choice.group_id not in groups:
            raise InvalidOptionSelection(
                "خيار غير متاح لهذا المنتج", "An option is not available for this product",
            )
        level_id, quantity = _selection_parts(raw_selection)
        if quantity <= 0:
            continue
        if (
            choice.group.display == "stepper"
            and choice.max_quantity
            and quantity > choice.max_quantity
        ):
            raise InvalidOptionSelection(
                f"{choice.name_ar or choice.name}: الحد الأقصى {choice.max_quantity}",
                f"{choice.name or choice.name_ar}: maximum quantity is {choice.max_quantity}",
            )
        if choice.group.uses_levels:
            level = levels.get(level_id)
            if level is None or level.group_id != choice.group_id:
                raise InvalidOptionSelection(
                    f"اختر مستوى لـ {choice.name_ar or choice.name}",
                    f"Pick a level for {choice.name or choice.name_ar}",
                )
            if level.is_none:
                continue
            active[choice_id] = {"level": level_id, "qty": 1}
        else:
            active[choice_id] = {
                "level": None,
                "qty": quantity if choice.group.display == "stepper" else 1,
            }
    counts = {}
    for choice_id, selection in active.items():
        choice = choices[choice_id]
        group = choice.group
        counts[group.id] = counts.get(group.id, 0) + 1

    for group_id, group in groups.items():
        count = counts.get(group_id, 0)
        if group.is_required and count == 0:
            raise InvalidOptionSelection(
                f"{group.name_ar or group.name} مطلوب",
                f"{group.name or group.name_ar} is required",
            )
        if group.max_select and count > group.max_select:
            raise InvalidOptionSelection(
                f"{group.name_ar or group.name}: الحد الأقصى {group.max_select}",
                f"{group.name or group.name_ar}: pick at most {group.max_select}",
            )

    lines = []
    # Stepper default quantity is included in the merchant's base price.
    # Credits below the default are opt-in; explicit zero quantities matter.
    for choice_id, raw_selection in selections.items():
        choice = choices[choice_id]  # Validated above, including zero-quantity entries
        _level_id, requested_quantity = _selection_parts(raw_selection)
        if choice.group.display == "stepper":
            billable_units = requested_quantity - choice.default_quantity
            if billable_units < 0 and not choice.deduct_below_default:
                billable_units = 0
        else:
            if choice_id not in active:
                continue
            billable_units = active[choice_id]["qty"]
        if not choice.price_delta or billable_units == 0:
            continue
        amount = choice.price_delta * billable_units
        lines.append({
            "kind": "choice",
            "choice_id": choice.id,
            "label": choice.label,
            "label_ar": choice.name_ar or choice.name,
            "label_en": choice.name or choice.name_ar,
            "quantity": requested_quantity,
            "charged_units": billable_units,
            "unit_amount": choice.price_delta,
            "amount": amount,
        })

    today = timezone.localdate()
    rules = (
        PricingRule.objects
        .filter(is_active=True)
        .filter(Q(applies_to_class__isnull=True) | Q(applies_to_class=pclass))
        .filter(Q(applies_to_product__isnull=True) | Q(applies_to_product=product))
        .filter(Q(starts_on__isnull=True) | Q(starts_on__lte=today))
        .filter(Q(ends_on__isnull=True) | Q(ends_on__gte=today))
        .select_related("market_index", "applies_to_product")
        .prefetch_related("conditions")
    )
    for rule in rules:
        conditions = list(rule.conditions.all())
        matches = all(
            condition.choice_id in active
            and (condition.level_id is None or active[condition.choice_id]["level"] == condition.level_id)
            for condition in conditions
        )
        if not matches:
            continue
        line = {
            "kind": "rule",
            "rule_id": rule.id,
            "label": rule.label,
            "label_ar": rule.name_ar or rule.name,
            "label_en": rule.name or rule.name_ar,
            "adjustment": rule.adjustment,
            "configured_amount": rule.amount,
        }
        if rule.adjustment == "fixed":
            amount = rule.amount
        elif rule.adjustment == "percent":
            amount = base_price * rule.amount / Decimal("100")
        elif rule.adjustment == "market":
            market_value = _market_value(rule.market_index)
            amount = market_value * rule.market_units * rule.amount
            line["market"] = {
                "index_id": rule.market_index_id,
                "code": rule.market_index.code,
                "name_ar": rule.market_index.name_ar or rule.market_index.name,
                "name_en": rule.market_index.name or rule.market_index.name_ar,
                "value": market_value,
                "currency": rule.market_index.currency,
                "unit": rule.market_index.unit,
                "units": rule.market_units,
                "multiplier": rule.amount,
                "last_updated": rule.market_index.last_updated,
            }
        else:
            continue
        line["amount"] = amount.quantize(CENT)
        lines.append(line)

    total = (base_price + sum((line["amount"] for line in lines), Decimal("0"))).quantize(CENT)
    if total < 0:
        raise OptionError(
            "السعر النهائي لا يمكن أن يكون سالباً",
            "Configured product price cannot be negative",
        )
    return {"base": base_price, "lines": lines, "total": total}
