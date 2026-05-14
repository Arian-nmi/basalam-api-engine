from website.models import BasalamConfig
from website.tasks.basalam_engine.client import BasalamAPIClient
from website.tasks.basalam_engine.image_uploader import BasalamImageUploader
from website.tasks.basalam_engine.creation import BasalamProductCreator
from website.tasks.basalam_engine.bs_bridge import build_basalam_models_for_shop_item


class CreateBasalamProduct:
    @staticmethod
    def publish_product(product):
        config = BasalamConfig.objects.filter(
            is_active=True,
            is_under_construction=False
        ).first()

        if not config or not config.v1_access_token:
            raise RuntimeError("BasalamConfig not configured")

        if not product.shop_item_id:
            raise ValueError("BasalamProduct.shop_item is required")

        client = BasalamAPIClient(config.v1_access_token)

        # product = build_basalam_models_for_shop_item(product.shop_item_id)

        uploader = BasalamImageUploader(product, client=client)
        uploader.upload_all()

        creator = BasalamProductCreator(product, client=client)
        return creator.create()
