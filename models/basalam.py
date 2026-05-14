from django.db import models
from website.models import (
    BaseModel, ProductionCategory, ColorInfo, SizeType,
    DesignerShopItems, User
)
from django.core.exceptions import ValidationError


class BasalamConfig(BaseModel):
    # Data Customic
    v1_access_token = models.TextField(null=True, blank=True)
    v1_refresh_token = models.TextField(null=True, blank=True)
    is_under_construction = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"BasalamConfig obj: {self.id}"


class BasalamProduct(BaseModel):
    BS_STATUS_CHOICES = [
        (2976, "published"),              # منتشر شده
        (3790, "unpublished"),            # منتشر نشده
        (3568, "waiting_for_confirm"),    # در انتظار تایید
        (4184, "illegal"),                # غیرقانونی
    ]
    UNIT_TYPE_CHOICES = [
        (6304, "numerical"),              # عددی
        (6308, "centimeter"),             # سانتی متر
        (6312, "millimeter"),             # میلی متر
    ]
    CATEGORY_CHOICES = [
        (324, "Mug"),
        (252, "T-Shirt Men"),
        (231, "T-Shirt Women"),
        (884, "Mousepad"),
    ]

    # Relations
    product_type = models.ForeignKey(
        ProductionCategory,
        on_delete=models.DO_NOTHING,
        related_name="basalam_products"
    )
    shop_item = models.OneToOneField(
        "DesignerShopItems",
        on_delete=models.CASCADE,
        related_name="basalam_product",
        null=False,
        blank=False
    )

    # Customic workflow status
    status = models.SlugField(max_length=50, default="initialize")
    admin_message = models.TextField(null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)

    # Basalam API data
    bsp_name = models.CharField(max_length=255, null=False, blank=False)  
    vendor_id = models.BigIntegerField(null=True, blank=True)
    category_id = models.PositiveIntegerField(choices=CATEGORY_CHOICES, null=False, blank=False, help_text="Product categories in Baslam")
    bsp_id = models.BigIntegerField(null=True, blank=True) 
    preparation_days = models.PositiveIntegerField(null=False, blank=False, default=3)
    brief = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    bs_status = models.PositiveIntegerField(choices=BS_STATUS_CHOICES, default=None, null=True, blank=True)
    unit_type = models.PositiveIntegerField(choices=UNIT_TYPE_CHOICES, default=6304)
    responses = models.JSONField(default=dict, blank=True)
    more_info = models.JSONField(default=dict, blank=True)
    photo = models.ImageField(upload_to="basalam/products/", null=True, blank=True)
    published_notified = models.BooleanField(default=False)
    failed_notified = models.BooleanField(default=False)
    def __str__(self):
        return f"BasalamProduct {self.id}-{self.status}"
        

class BasalamVariant(BaseModel):
    # Relations
    basalam_product = models.ForeignKey(
        BasalamProduct,
        on_delete=models.CASCADE,
        related_name="variants"
    )

    color = models.ForeignKey(
        ColorInfo,
        on_delete=models.DO_NOTHING
    )

    size = models.ForeignKey(
        SizeType,
        on_delete=models.DO_NOTHING
    )

    # Data
    primary_price = models.PositiveIntegerField(null=True, blank=True, default=0)
    stock = models.IntegerField(null=True, blank=True, default=0)
    sku = models.CharField(max_length=100, unique=True)
    is_wholesale = models.BooleanField(default=False)
    weight = models.PositiveIntegerField(null=True, blank=True)
    package_weight = models.PositiveIntegerField(null=False, blank=False, default=100)
    properties = models.JSONField(blank=True)

    class Meta:
        unique_together = (
            "basalam_product",
            "color",
            "size",
        )

    # def clean(self):
    #     super().clean()
    #
    #     if self.weight is None or self.weight <= 0:
    #         raise ValidationError({
    #             "weight": "production_info.weight must be > 0 (Basalam rejects weight=0)"
    #         })
    #
    #     if self.package_weight is None or self.package_weight <= 0:
    #         raise ValidationError({
    #             "package_weight": "production_info.package_weight must be > 0 (Basalam will error otherwise)"
    #         })
    #
    #     if self.weight is not None and self.package_weight is not None and self.package_weight <= self.weight:
    #         raise ValidationError({
    #             "package_weight": "production_info.package_weight must be > production_info.weight (Basalam rule)"
    #         })
    #
    # def save(self, *args, **kwargs):
    #     self.full_clean()
    #     return super().save(*args, **kwargs)


    def __str__(self):
        return f"Variant {self.sku}-{self.color}-{self.size}"


class BSProductImage(BaseModel):
    # Relation
    basalam_product = models.ForeignKey(
        BasalamProduct,
        on_delete=models.CASCADE,
        related_name="images"
    )

    # Data
    file_id = models.BigIntegerField(null=True, blank=True, help_text="Basalam uploaded image id")
    order = models.PositiveSmallIntegerField(default=0, help_text="Order of image in Basalam product gallery(0 = main image)")

    class Meta:
        ordering = ["order"]
        unique_together = ("basalam_product", "order")

    def __str__(self):
        return f"BSProductImage {self.basalam_product_id} | order={self.order}"


class BasalamAbilities(BaseModel):
    # Relation
    user = models.OneToOneField(
        User,
        on_delete=models.DO_NOTHING,
        related_name="basalam_abilities",
        null=False,
        blank=False
    )
    
    # Data
    basalam_request_capacity = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"BasalamAbilities obj: {self.id}-{self.user}-{self.basalam_request_capacity}"
