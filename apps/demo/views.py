"""Minimal, read-only product catalogue + non-payment price/snapshot endpoints.

The quote never accepts client-submitted prices. It feeds selections into the
EXACT SAME real B2 compute_price() logic preserved in apps/options/pricing.py.
"""
import json
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from django.utils import translation, timezone

from apps.catalogue.models import Product
from apps.options.models import OptionGroup, OptionChoice, OptionLevel, ProductClassOption
from apps.options.pricing import OptionError, compute_price
from .models import DemoOrderSnapshot

CENT = Decimal("0.01")


def safe_json(value):
    """JSON-safe public scalar values; no hidden provider credentials exist."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(k): safe_json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [safe_json(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _serialize_product(product):
    links = ProductClassOption.objects.filter(product_class=product.get_product_class(), group__is_active=True).select_related("group").order_by("sort_order", "group__sort_order")
    groups = []
    defaults = {}
    for link in links:
        group = link.group
        choices = list(group.choices.filter(is_active=True).order_by("sort_order", "id"))
        levels = list(group.levels.all().order_by("sort_order", "id"))
        data = {
            "id": group.id, "name": group.name, "name_ar": group.name_ar,
            "display": group.display, "uses_levels": group.uses_levels,
            "is_required": group.is_required, "max_select": group.max_select,
            "levels": [{"id": lv.id, "name": lv.name, "name_ar": lv.name_ar, "is_none": lv.is_none, "is_default": lv.is_default} for lv in levels],
            "choices": [{"id": c.id, "name": c.name, "name_ar": c.name_ar, "color": c.swatch_hex,
                         "price_delta": str(c.price_delta), "default_quantity": c.default_quantity,
                         "max_quantity": c.max_quantity, "deduct_below_default": c.deduct_below_default,
                         "is_default": c.is_default} for c in choices],
        }
        groups.append(data)
        if group.display == "stepper":
            # Include 0-quantity stepper selections to preserve opt-in credits.
            for choice in choices:
                defaults[str(choice.id)] = {"level": None, "qty": choice.default_quantity}
        elif group.uses_levels:
            level = next((l for l in levels if l.is_default), levels[0] if levels else None)
            for choice in choices:
                if choice.is_default and level and not level.is_none:
                    defaults[str(choice.id)] = {"level": level.id, "qty": 1}
        else:
            default_choices = [c for c in choices if c.is_default]
            if not default_choices and group.is_required and choices:
                default_choices = [choices[0]]
            for choice in default_choices:
                defaults[str(choice.id)] = {"level": None, "qty": 1}
    return {
        "slug": product.slug, "title": product.title, "description": product.description,
        "category": product.product_class.name, "base_price": str(product.base_price),
        "accent": product.accent, "icon": product.icon, "groups": groups,
        "defaults": defaults,
    }


def _body(request):
    if len(request.body) > 32768:
        raise ValueError("Request exceeds the demo size limit.")
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Expected valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Request must contain a JSON object.")
    return payload


def _normalize(raw):
    """Adapted from B2 apps/options/views.py::_normalise_selections."""
    if not isinstance(raw, dict) or len(raw) > 200:
        raise ValueError("Selections must be an object with at most 200 entries.")
    data = {}
    for key, value in raw.items():
        try:
            choice_id = int(key)
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid choice ID.") from exc
        if choice_id <= 0 or not isinstance(value, dict):
            raise ValueError("Invalid option selection.")
        level_raw = value.get("level")
        if level_raw in (None, ""):
            level = None
        else:
            try:
                level = int(level_raw)
            except (ValueError, TypeError) as exc:
                raise ValueError("Invalid level ID.") from exc
            if level <= 0:
                raise ValueError("Invalid level ID.")
        try:
            # Reject float values and number strings such as "1.5"; preserve real quantity semantics.
            if isinstance(value.get("qty", 1), bool):
                raise ValueError()
            qty = int(value.get("qty", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid option quantity.") from exc
        if qty < 0 or qty > 100000:
            raise ValueError("Option quantity outside permitted bounds.")
        data[choice_id] = {"level": level, "qty": qty}
    return dict(sorted(data.items()))


def _calculate(payload):
    product = get_object_or_404(Product, slug=str(payload.get("product_slug", "")))
    selections = _normalize(payload.get("selections", {}))
    result = compute_price(product, product.base_price, selections)
    rate = Decimal(settings.DEMO_VAT_RATE)
    tax = (result["total"] * rate).quantize(CENT, rounding=ROUND_HALF_UP)
    breakdown = safe_json(result)
    return product, selections, {
        "product": product.title, "currency": "SAR", "base": breakdown["base"],
        "adjustments": breakdown["lines"], "subtotal": breakdown["total"],
        "vat_rate": str(rate), "vat": str(tax),
        "total": str(result["total"] + tax),
        "note": "Illustrative Saudi VAT for this local demo. No payments are processed.",
    }


@ensure_csrf_cookie
@require_GET
def index(request):
    return render(request, "demo/index.html")


@require_GET
def products(request):
    return JsonResponse({"products": [{"slug": p.slug, "title": p.title, "category": p.product_class.name, "icon": p.icon} for p in Product.objects.select_related("product_class").order_by("id")]})


@require_GET
def product_detail(request, slug):
    return JsonResponse(_serialize_product(get_object_or_404(Product.objects.select_related("product_class"), slug=slug)))


@require_POST
def quote(request):
    try:
        _product, _selections, result = _calculate(_body(request))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except OptionError as exc:
        return JsonResponse({"error": exc.message(), "type": exc.__class__.__name__}, status=422)
    return JsonResponse(result)


@require_POST
def snapshot_create(request):
    """Persist a sample quote as a frozen DEMO record; no order/payment is placed."""
    try:
        product, selections, result = _calculate(_body(request))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except OptionError as exc:
        return JsonResponse({"error": exc.message()}, status=422)
    # Freeze display labels and all authoritative adjustment inputs at creation.
    option_choices = OptionChoice.objects.filter(id__in=selections).select_related("group")
    choice_map = {choice.id: choice for choice in option_choices}
    levels = OptionLevel.objects.filter(id__in=[value["level"] for value in selections.values() if value["level"]])
    level_map = {level.id: level for level in levels}
    chosen = []
    for choice_id, selected in sorted(selections.items()):
        choice = choice_map[choice_id]
        level = level_map.get(selected["level"])
        chosen.append({
            "group": {"en": choice.group.name, "ar": choice.group.name_ar},
            "choice": {"en": choice.name, "ar": choice.name_ar},
            "quantity": selected["qty"],
            "level": None if not level else {"en": level.name, "ar": level.name_ar},
        })
    frozen = {
        "version": 1,
        "product": {"slug": product.slug, "title": product.title},
        "selected_options": chosen,
        "pricing": result,
        "recorded_at": timezone.now().isoformat(),
        "demo_only": True,
    }
    stored = DemoOrderSnapshot.objects.create(product=product, frozen_data=frozen)
    return JsonResponse({"id": str(stored.pk), "snapshot": frozen}, status=201)


@require_GET
def snapshot_detail(request, pk):
    return JsonResponse({"id": str(pk), "snapshot": get_object_or_404(DemoOrderSnapshot, pk=pk).frozen_data})
