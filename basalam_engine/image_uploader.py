import mimetypes
from os.path import basename
from django.core.files.storage import default_storage
from website.models import BasalamConfig
from .client import BasalamAPIClient


class BasalamImageUploader:
    FILE_TYPE = "product.photo"

    def __init__(self, product, client=None):
        self.product = product

        if client is not None:
            self.client = client
            return

        config = BasalamConfig.objects.filter(
            is_active=True,
            is_under_construction=False
        ).first()

        if not config or not config.v1_access_token:
            raise RuntimeError("BasalamConfig is not configured")

        self.client = BasalamAPIClient(config.v1_access_token)

    def _get_photos(self) -> list[dict]:
        more = self.product.more_info or {}
        photos = more.get("photos") or []
        if not isinstance(photos, list):
            raise ValueError("BasalamProduct.more_info['photos'] must be a list")
        return photos

    def _save_photos(self, photos: list[dict]) -> None:
        more = self.product.more_info or {}
        more["photos"] = photos
        self.product.more_info = more
        self.product.save(update_fields=["more_info"])

    def _upload_path(self, path: str) -> int:
        with default_storage.open(path, "rb") as f:
            file_bytes = f.read()

        file_name = basename(path)
        mime_type = mimetypes.guess_type(file_name)[0] or "image/jpeg"

        response = self.client.post(
            url="/v1/files",
            files={"file": (file_name, file_bytes, mime_type)},
            data={"file_type": self.FILE_TYPE},
        )

        if response.status_code not in (200, 201):
            raise Exception(f"Upload failed [{response.status_code}]: {response.text}")

        data = response.json()
        return int(data["id"])

    def upload_single(self, order: int = 0) -> int:
        """
        Uploads a photo from more_info['photos'] based on order.
        """
        photos = self._get_photos()
        if not photos:
            raise ValueError("BasalamProduct.more_info['photos'] is empty")

        photo = next((p for p in photos if int(p.get("order", 0)) == int(order)), None)
        if not photo:
            raise ValueError(f"No photo found with order={order}")

        if photo.get("file_id"):
            return int(photo["file_id"])

        path = photo.get("path")
        if not path:
            raise ValueError("Photo item has no 'path'")

        file_id = self._upload_path(path)
        photo["file_id"] = file_id
        self._save_photos(photos)
        return file_id

    def upload_all(self) -> None:
        """
        upload all photos that have no file_id
        """
        photos = self._get_photos()
        if not photos:
            raise ValueError("BasalamProduct.more_info['photos'] is empty")

        changed = False
        for photo in photos:
            if photo.get("file_id"):
                continue

            path = photo.get("path")
            if not path:
                raise ValueError("Photo item has no 'path'")

            photo["file_id"] = self._upload_path(path)
            changed = True

        if changed:
            self._save_photos(photos)
