from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="demo-home"),
    path("api/products/", views.products, name="demo-products"),
    path("api/products/<slug:slug>/", views.product_detail, name="demo-product"),
    path("api/quote/", views.quote, name="demo-quote"),
    path("api/snapshots/", views.snapshot_create, name="demo-snapshot-create"),
    path("api/snapshots/<uuid:pk>/", views.snapshot_detail, name="demo-snapshot-detail"),
]
