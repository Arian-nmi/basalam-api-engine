from django.db import transaction
from django.db.models import Case, When, IntegerField
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from website.tools.telegram_methods import SendCustomicReportMessageThread
from website.models import (
    DesignerShopItems, BasalamProduct, BasalamVariant,
    DetailInfo, MockupImage
)


STATIC_BASALAM_STOCK = 4

class BasalamBuildError(Exception):
    def __init__(self, step: str, message: str):
        self.step = step
        self.message = message
        super().__init__(f"[{step}] {message}")


def first_available_image_field(mockup: MockupImage):
    for f in ("image_large", "image"):
        val = getattr(mockup, f, None)
        if val:
            return val

    raise BasalamBuildError(
        step="VALIDATION.FOUND_IMAGE",
        message="No image found on MockupImage. Expected one of: image_large, image"
    )


def color_label(color) -> str:
    return (
        (getattr(color, "visual_color_name", None) or "").strip()
        or (getattr(color, "color_name", None) or "").strip()
        or "تک‌ رنگ"
    )


def area_priority_for_basalam(shop_item: DesignerShopItems) -> list[str]:
    product_type = getattr(getattr(shop_item, "seller_design", None), "category", None)
    t = (getattr(product_type, "type", "") or "").strip().lower()

    if "mug" in t:
        return ["front", "right", "left", "back"]
    if "mousepad" in t:
        return ["front"]
    if "tshirt" in t or "t-shirt" in t or "tee" in t:
        return ["front", "back", "left", "right"]

    return ["front", "back", "right", "left"]


def pick_ranked_dk_thumbnails(shop_item: DesignerShopItems):
    qs = MockupImage.objects.filter(
        seller_design=shop_item.seller_design,
        is_dk_thumbnail=True,
    )

    if not qs.exists():
        return qs  

    preferred_areas = area_priority_for_basalam(shop_item) or []
    whens = [When(area=a, then=i) for i, a in enumerate(preferred_areas)]

    return qs.annotate(
        _area_rank=Case(
            *whens,
            default=len(preferred_areas),
            output_field=IntegerField()
        )
    ).order_by("_area_rank", "id")


def build_photos_from_mockup_images(shop_item: DesignerShopItems) -> tuple[list[dict], object]:
    qs = pick_ranked_dk_thumbnails(shop_item)
    if not qs.exists():
        raise BasalamBuildError(
            step="VALIDATION.BUILD_PHOTOS",
            message="No MockupImage with is_dk_thumbnail=True found for this seller_design"
        )

    photos = []
    main_file = None
    seen_paths = set()

    for m in qs:
        img = first_available_image_field(m)
        if not img:
            continue

        path = img.name
        if not path or path in seen_paths:
            continue

        if main_file is None:
            main_file = img

        photos.append({
            "order": len(photos),
            "path": path,
            "file_id": None,
        })
        seen_paths.add(path)

    if not photos or main_file is None:
        raise BasalamBuildError(
            step="VALIDATION.BUILD_PHOTOS",
            message="DK thumbnails exist but none had usable image fields"
        )

    return photos, main_file


def determine_basalam_category_id(product_type) -> int:
    t = (getattr(product_type, "type", "") or "").strip().lower()
    if "mug" in t:
        return 324
    if "mousepad" in t:
        return 884
    if "tshirt" in t or "t-shirt" in t or "tee" in t:
        if "women" in t or "female" in t or "woman" in t:
            return 231
        return 252

    raise BasalamBuildError(
        step="VALIDATION.DETERMINE_CATEGORY_ID",
        message=f"Unknown ProductionCategory.type={t!r} for basalam category mapping"
    )


def generate_basalam_product_name(shop_item: DesignerShopItems) -> str:
    product_type = shop_item.seller_design.category
    production_info = shop_item.production_info

    base_name = (
        shop_item.customic_name
        or shop_item.name
    )

    t = (product_type.type or "").lower()

    if "tshirt" in t or "t-shirt" in t:
        gender = "مردانه"
        if "women" in t or "female" in t:
            gender = "زنانه"

        return f"تیشرت آستین کوتاه {gender} مدل {base_name}"

    if "mug" in t:
        if production_info and "حرارتی" in (production_info.name or ""):
            return f"ماگ حرارتی مدل {base_name}"
        return f"ماگ مدل {base_name}"

    if "mousepad" in t:
        return f"ماوس پد مدل {base_name}"

    return base_name


def generate_basalam_product_brief(shop_item: DesignerShopItems) -> str:
    if shop_item.customic_name:
        return shop_item.customic_name
    
    return


def generate_basalam_product_info(shop_item: DesignerShopItems) -> str:
    if shop_item.description:
        return shop_item.description


def compute_primary_price(shop_item: DesignerShopItems, detail: DetailInfo) -> int:
    base = int(detail.price_base or 0)
    seller_profit = int(shop_item.seller_profit or 0)
    platform_print = int(getattr(shop_item.seller_design, "price_platform_print", 0) or 0)
    return base + seller_profit + platform_print


def toman_to_rial(price_toman: int) -> int:
    return int(price_toman) * 10


def make_sku(shop_item_id: int, size_id: int, color_id: int) -> str:
    return f"BS-{shop_item_id}-{size_id}-{color_id}"


def merge_file_ids_by_path(old_photos, new_photos: list[dict]) -> list[dict]:
    old_map = {}
    if isinstance(old_photos, list):
        for p in old_photos:
            if not isinstance(p, dict):
                continue
            path = p.get("path")
            file_id = p.get("file_id")
            if path and file_id:
                old_map[path] = int(file_id)

    for p in new_photos:
        path = p.get("path")
        if path in old_map and not p.get("file_id"):
            p["file_id"] = old_map[path]

    return new_photos


def build_basalam_models_for_shop_item(shop_item_id: int) -> BasalamProduct:
    shop_item = (
        DesignerShopItems.objects
        .select_related("seller_design", "seller_design__category", "production_info")
        .prefetch_related("selected_colors")
        .get(id=shop_item_id)
    )

    if not shop_item.has_basalam_request:
        raise BasalamBuildError(
            step="VALIDATION.BUILD_BASALAM_MODEL_FOR_SHOP_ITEM",
            message=f"shop_item.has_basalam_request is False"
        )
    if shop_item.is_design_removed:
        raise BasalamBuildError(
            step="VALIDATION.BUILD_BASALAM_MODEL_FOR_SHOP_ITEM",
            message=f"shop_item.is_design_removed is True"
        )
    if not shop_item.production_info_id:
        raise BasalamBuildError(
            step="VALIDATION.BUILD_BASALAM_MODEL_FOR_SHOP_ITEM",
            message=f"shop_item.production_info is NULL"
        )

    weight = int(getattr(shop_item.production_info, "weight", 0) or 0)
    package_weight = int(getattr(shop_item.production_info, "package_weight", 0) or 0)

    if weight is None or int(weight or 0) <= 0:
        raise BasalamBuildError(
            step="VALIDATION.BUILD_BASALAM_MODEL_FOR_SHOP_ITEM",
            message=f"production_info.weight must be > 0"
        )
    if package_weight is None or int(package_weight or 0) <= 0:
        raise BasalamBuildError(
            step="VALIDATION.BUILD_BASALAM_MODEL_FOR_SHOP_ITEM",
            message=f"production_info.package_weight must be > 0"
        )
    if int(package_weight) <= int(weight):
        raise BasalamBuildError(
            step="VALIDATION.BUILD_BASALAM_MODEL_FOR_SHOP_ITEM",
            message=f"production_info.package_weight must be > production_info.weight"
        )
        
    product_type = shop_item.seller_design.category
    category_id = determine_basalam_category_id(product_type)

    with transaction.atomic():
        bsp_name = generate_basalam_product_name(shop_item)
        brief = generate_basalam_product_brief(shop_item)
        description = generate_basalam_product_info(shop_item)

        bp, _ = BasalamProduct.objects.update_or_create(
            shop_item=shop_item,
            defaults={
                "product_type": product_type,
                "category_id": category_id,
                "bsp_name": bsp_name,
                "brief": brief,
                "description": description,
                "preparation_days": 3,
            }
        )

        new_photos, main_file = build_photos_from_mockup_images(shop_item)
        old_photos = (bp.more_info or {}).get("photos")
        new_photos = merge_file_ids_by_path(old_photos, new_photos)
        more = bp.more_info or {}
        more["photos"] = new_photos
        bp.more_info = more
        bp.photo = main_file
        bp.save(update_fields=["photo", "more_info"])
        raw_colors = list(shop_item.selected_colors.all())

        if not raw_colors:
            raise BasalamBuildError(
            step="VALIDATION.BUILD_BASALAM_MODEL_FOR_SHOP_ITEM",
            message=f"shop_item.selected_colors is empty"
        )

        details = (
            DetailInfo.objects
            .select_related("size_type")
            .filter(production_info=shop_item.production_info)
            .order_by("id")
        )
        if not details.exists():
            raise BasalamBuildError(
            step="VALIDATION.BUILD_BASALAM_MODEL_FOR_SHOP_ITEM",
            message=f"No DetailInfo found for shop_item.production_info"
        )

        color_groups = {}
        for c in raw_colors:
            label = color_label(c)
            color_groups.setdefault(label, []).append(c)

        bp.variants.all().delete()

        for detail in details:
            for _, colors in color_groups.items():
                canonical = min(colors, key=lambda x: x.id)
                primary_price = toman_to_rial(compute_primary_price(shop_item, detail))
                sku = make_sku(shop_item.id, detail.size_type_id, canonical.id)

                BasalamVariant.objects.update_or_create(
                    basalam_product=bp,
                    color=canonical,
                    size=detail.size_type,
                    defaults={
                        "primary_price": primary_price,
                        "stock": STATIC_BASALAM_STOCK,
                        "sku": sku,
                        "weight": weight,
                        "package_weight": package_weight,
                        "properties": [],
                        "is_wholesale": False,
                    }
                )
                
        if shop_item.basalam_status != "fully-added":
                shop_item.basalam_status = "fully-added"
                shop_item.save(update_fields=["basalam_status"])
                send_basalam_created_notification(bp)

        return bp


def send_basalam_created_notification(bp: BasalamProduct):
    shop_item = bp.shop_item
    print("========= SEND_BASALAM_NOTIFICATION CALLED =========", bp.id)

    SendCustomicReportMessageThread(
        type="باسلام",
        thread_number=370,
        message="new basalam request!\n\n" \
            + f"bs instance id: {bp.id}" + "\n" \
            + f"shop item id: {shop_item.id}" + "\n" \
            + f"shop item slug: {shop_item.slug_name}" + "\n" \
            + f"shop slug: {shop_item.shop.slug_name}" + "\n" \
            + f"product: {shop_item.production_info.name}" + "\n" \
            + f"user bs name: {bp.bsp_name}" + "\n" \
            + f"status: fully-added"
    ).start()

# -------------------------
# Telegram notifications
# -------------------------
@receiver(post_save, sender=BasalamProduct)
def update_basalam_product_status(sender, instance, created, **kwargs):
    """
    Sync BasalamProduct.bs_status with DesignerShopItems.basalam_status
    and send Telegram notifications exactly once.
    """
    if created:
        return

    bp = instance
    shop_item = bp.shop_item

    # -------------------------
    # FAILED
    # -------------------------
    if bp.bs_status == 4184 and not bp.failed_notified:
        shop_item.basalam_status = "sth-went-wrong"
        shop_item.save(update_fields=["basalam_status"])

        bp.failed_notified = True
        bp.save(update_fields=["failed_notified"])

        pi = shop_item.production_info
        SendCustomicReportMessageThread(
            type="باسلام",
            thread_number=370,
            message="❌ Basalam product FAILED\n\n"
                    + f"name: {pi.name}\n"
                    + f"Basalam product id: {bp.id}\n"
                    + f"bs_status: {bp.bs_status}\n"
                    + f"shop slug: {shop_item.shop.slug_name}\n"
                    + f"shop item id: {shop_item.id}\n"
        ).start()
        return

    # -------------------------
    # PUBLISHED
    # -------------------------
    if bp.bs_status == 2976 and not bp.published_notified:
        shop_item.basalam_status = "fully-added"
        shop_item.save(update_fields=["basalam_status"])

        bp.published_notified = True
        bp.save(update_fields=["published_notified"])

        SendCustomicReportMessageThread(
            type="باسلام",
            thread_number=370,
            message="✅ Basalam product PUBLISHED\n\n"
                    + f"Basalam product id: {bp.id}\n"
                    + f"shop item id: {shop_item.id}\n"
                    + f"shop slug: {shop_item.shop.slug_name}\n"
        ).start()
