from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Organisation, Store, User


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "phone", "created_at")


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "organisation", "is_default")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "organisation", "role", "is_active")
    list_filter = ("role", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Organisation", {"fields": ("organisation", "role", "phone", "store")}),
    )
