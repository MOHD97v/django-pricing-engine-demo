"""Minimal stand-ins for Oscar's ProductClass and Product.

Original B2 pricing calls product.get_product_class(). In this standalone demo,
these two tiny models provide that API without pulling in the entire Oscar shop.
"""
from django.db import models

class ProductClass(models.Model):
    name = models.CharField(max_length=120, unique=True)
    def __str__(self):
        return self.name

class Product(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    product_class = models.ForeignKey(ProductClass, on_delete=models.PROTECT)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    accent = models.CharField(max_length=16, default="#67867B")
    icon = models.CharField(max_length=16, default="✦")

    def get_product_class(self):
        return self.product_class

    def __str__(self):
        return self.title
