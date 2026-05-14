from celery import shared_task
from django_redis import get_redis_connection
from website.models import BasalamConfig, DesignerShopItems
from website.tasks.basalam_engine.bs_bridge import (build_basalam_models_for_shop_item, BasalamBuildError)


@shared_task(name="website.tasks.basalam_engine.bs_routine_tasks.prepare_and_queue_basalam_products")
def prepare_and_queue_basalam_products(limit=20):
    config = BasalamConfig.objects.filter(is_active=True, is_under_construction=False).first()
    if not config or not config.is_active:
        print("[Basalam] system inactive")
        return

    shop_items = (
        DesignerShopItems.objects
        .filter(
            has_basalam_request=True,
            basalam_status="not-done",
            is_design_removed=False,
            is_approved=True,
            is_rejected=False
        )
        .order_by("id")[:limit]
    )

    redis_conn = get_redis_connection("default")
    queued = 0
    failed = 0

    for si in shop_items:
        try:
            bp = build_basalam_models_for_shop_item(si.id)

            if bp.status in ("queued", "processing", "done"):
                continue

            bp.status = "queued"
            bp.save(update_fields=["status"])
            redis_conn.lpush("basalam_product_queue", bp.id)
            queued += 1

        except BasalamBuildError as e:
            failed += 1
            si.basalam_status = "imperfect"
            si.basalam_error_step = e.step
            si.basalam_error_message = e.message
            si.save(update_fields=[
                "basalam_status",
                "basalam_error_step",
                "basalam_error_message"
            ])

        except Exception as e:
            failed += 1
            si.basalam_status = "imperfect"
            si.basalam_error_step = "UNKNOWN"
            si.basalam_error_message = str(e)
            si.save()
            print(f"[Basalam] prepare error shop_item={si.id}: {type(e).__name__}: {e}")

    print(f"[Basalam] prepared+queued={queued} failed={failed}")
