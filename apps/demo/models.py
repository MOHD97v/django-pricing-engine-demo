"""Local demonstration snapshots, NOT actual purchases or payment records."""
import uuid
from django.db import models

class DemoOrderSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey("catalogue.Product", null=True, on_delete=models.SET_NULL)
    frozen_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
