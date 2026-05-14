from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from website.models import(
    BasalamConfig, BasalamProduct, 
    BasalamVariant, BSProductImage, BasalamAbilities
)


class BasalamConfigAdmin(admin.ModelAdmin):
    list_display = [
        "id", "is_active", "is_under_construction", "v1_access_token", "v1_refresh_token"
    ]
    ordering = ["-id"]

admin.site.register(BasalamConfig, BasalamConfigAdmin)


class BSProductImageInline(admin.TabularInline):
    model = BSProductImage
    extra = 1
    fields = ("id", "order", "file_id")
    readonly_fields = ("file_id",)


class BasalamProductAdmin(admin.ModelAdmin):
    list_display = [
        "id", "bsp_name", "product_type", "shop_item", "status", "category_id", "brief", "bs_status", "photo",
    ]
    ordering = ["-id"]
    inlines = [BSProductImageInline]

admin.site.register(BasalamProduct, BasalamProductAdmin)


class BasalamVariantAdmin(admin.ModelAdmin):
    list_display = [
        "id", "basalam_product", "primary_price", "stock", "sku", "is_wholesale", "weight", "package_weight"
    ]
    ordering = ["-id"]

admin.site.register(BasalamVariant, BasalamVariantAdmin)


class BasalamAbilitiesAdmin(admin.ModelAdmin):
    list_display = [
        "id", "user", "basalam_request_capacity"
    ]
    ordering = ["-id"]

admin.site.register(BasalamAbilities, BasalamAbilitiesAdmin)
