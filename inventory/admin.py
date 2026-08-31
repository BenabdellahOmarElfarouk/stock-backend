from django.contrib import admin

from .models import Stock, StockMovement

admin.site.register(Stock)
admin.site.register(StockMovement)
