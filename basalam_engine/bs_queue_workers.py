from django_redis import get_redis_connection
from core.celery import app
from website.models import BasalamProduct
from website.tasks.basalam_engine.product import CreateBasalamProduct


@app.task(name="website.tasks.basalam_engine.bs_queue_workers.start_basalam_workers")
def start_basalam_workers():
    process_basalam_queue.apply_async(queue="basalam_worker_1")
    # process_basalam_queue.apply_async(queue="basalam_worker_2")
    print("[Basalam] workers started")


@app.task(bind=True, name="website.tasks.basalam_engine.bs_queue_workers.process_basalam_queue")
def process_basalam_queue(self):
    redis_conn = get_redis_connection("default")
    product = None

    try:
        item = redis_conn.brpop("basalam_product_queue", timeout=5)
        if not item:
            return

        product_id = int(item[1].decode())
        product = BasalamProduct.objects.get(id=product_id)

        print(f"[Basalam] processing product {product_id}")

        product.status = "processing"
        product.save(update_fields=["status"])

        CreateBasalamProduct.publish_product(product)

        product.status = "done"
        product.save(update_fields=["status"])
        print(f"[Basalam] product {product_id} done")

    except Exception as e:
        print(f"[Basalam] worker error: {e}")
        if product:
            product.status = "failed"
            product.admin_message = str(e)
            product.save(update_fields=["status", "admin_message"])
