from django.contrib import admin

from .models import Customer, Supplier

admin.site.register(Customer)
admin.site.register(Supplier)
