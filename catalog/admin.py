from django.contrib import admin

from .models import Article, Category, PaymentMethod, TaxRate, Unit

admin.site.register(Category)
admin.site.register(Unit)
admin.site.register(TaxRate)
admin.site.register(PaymentMethod)
admin.site.register(Article)
