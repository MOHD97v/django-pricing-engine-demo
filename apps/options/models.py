"""Focused adaptation of Modomutiorga/B2-Store apps/options/models.py.

Preserves the pricing engine's real ORM model names and relations. Image uploads,
provider credentials, and Oscar-only catalogue/checkout models are omitted from
this PUBLIC, LOCAL demo; see docs/SOURCE_MAP.md for exact scope.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import translation

class Bilingual(models.Model):
    name = models.CharField("Name (English)", max_length=100, blank=True)
    name_ar = models.CharField("الاسم (عربي)", max_length=100)

    class Meta:
        abstract = True

    @property
    def label(self):
        language = translation.get_language() or ""
        if language.startswith("ar") and self.name_ar:
            return self.name_ar
        return self.name or self.name_ar

    def __str__(self):
        return self.label

class OptionGroup(Bilingual):
    DISPLAY_CHOICES = [
        ("dropdown", "Dropdown"), ("chips", "Buttons / chips"),
        ("swatch", "Color swatches"), ("image", "Image tiles"),
        ("radio", "Radio list"), ("checkbox", "Checkbox list"),
        ("levels", "Segmented levels"), ("stepper", "+ / - stepper"),
    ]
    slug = models.SlugField(unique=True)
    display = models.CharField(max_length=20, choices=DISPLAY_CHOICES, default="chips")
    uses_levels = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    max_select = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

class OptionChoice(Bilingual):
    group = models.ForeignKey(OptionGroup, related_name="choices", on_delete=models.CASCADE)
    slug = models.SlugField()
    swatch_hex = models.CharField(max_length=7, blank=True)
    price_delta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    default_quantity = models.PositiveSmallIntegerField(default=0)
    deduct_below_default = models.BooleanField(default=False)
    max_quantity = models.PositiveSmallIntegerField(default=0)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = [("group", "slug")]

class OptionLevel(Bilingual):
    group = models.ForeignKey(OptionGroup, related_name="levels", on_delete=models.CASCADE)
    is_none = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        unique_together = [("group", "name_ar")]

class ProductClassOption(models.Model):
    product_class = models.ForeignKey("catalogue.ProductClass", related_name="option_links", on_delete=models.CASCADE)
    group = models.ForeignKey(OptionGroup, on_delete=models.CASCADE)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        unique_together = [("product_class", "group")]

class MarketIndex(Bilingual):
    # Demo only stores a market rate; it does NOT call a live provider.
    code = models.SlugField(unique=True)
    provider = models.CharField(max_length=30, default="manual")
    current_value = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    currency = models.CharField(max_length=3, default="SAR")
    unit = models.CharField(max_length=10, default="g")
    max_age_minutes = models.PositiveIntegerField(default=180)
    last_updated = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label

class PricingRule(Bilingual):
    ADJUSTMENTS = [("fixed", "Fixed amount"), ("percent", "Percent of base"), ("market", "Market index × units × multiplier")]
    applies_to_class = models.ForeignKey("catalogue.ProductClass", null=True, blank=True, on_delete=models.CASCADE)
    applies_to_product = models.ForeignKey("catalogue.Product", null=True, blank=True, on_delete=models.CASCADE)
    adjustment = models.CharField(max_length=10, choices=ADJUSTMENTS, default="fixed")
    amount = models.DecimalField(max_digits=12, decimal_places=4)
    market_index = models.ForeignKey(MarketIndex, null=True, blank=True, on_delete=models.PROTECT, related_name="pricing_rules")
    market_units = models.DecimalField(max_digits=12, decimal_places=4, default=1)
    is_active = models.BooleanField(default=True)
    show_on_storefront = models.BooleanField(default=False)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)

    def clean(self):
        super().clean()
        if self.adjustment == "market" and not self.market_index:
            raise ValidationError({"market_index": "A market index is required for a market pricing rule."})
        if self.applies_to_product_id and self.applies_to_class_id and self.applies_to_product.get_product_class() != self.applies_to_class:
            raise ValidationError({"applies_to_product": "The selected product does not belong to this product type."})

class RuleCondition(models.Model):
    rule = models.ForeignKey(PricingRule, related_name="conditions", on_delete=models.CASCADE)
    choice = models.ForeignKey(OptionChoice, on_delete=models.CASCADE)
    level = models.ForeignKey(OptionLevel, null=True, blank=True, on_delete=models.CASCADE)

    def clean(self):
        super().clean()
        if self.choice_id and self.level_id and self.choice.group_id != self.level.group_id:
            raise ValidationError({"level": "The selected level must belong to the same option group as the choice."})
