from .client import BasalamAPIClient
from .payloads import BasalamProductPayloadBuilder
from .service import BasalamVendorService
from website.models import BasalamConfig


class BasalamProductCreator:

    def __init__(self, basalam_product, client=None):
        self.product = basalam_product

        if client is not None:
            self.client = client
        else:
            config = BasalamConfig.objects.filter(
                is_active=True,
                is_under_construction=False
            ).first()

            if not config or not config.v1_access_token:
                raise RuntimeError("BasalamConfig is not configured")

            self.client = BasalamAPIClient(config.v1_access_token)
        self.vendor_service = BasalamVendorService(self.client)

    def create(self):
        if self.product.bsp_id:
            print(f"Already created in Basalam (bsp_id={self.product.bsp_id}), skipping create.")
            return self.product

        existing_id = (self.product.responses or {}).get("create", {}).get("data", {}).get("id")
        if existing_id and not self.product.bsp_id:
            self.product.bsp_id = int(existing_id)
            self.product.save(update_fields=["bsp_id"])
            print(f"Recovered bsp_id from responses: {self.product.bsp_id}")
            return self.product

        if not self.product.vendor_id:
            try:
                fetched_id = self.vendor_service.get_or_fetch_vendor_id()
                self.product.vendor_id = fetched_id
                self.product.save(update_fields=["vendor_id"])
            except Exception as e:
                self.product.responses["vendor_error"] = str(e)
                self.product.save(update_fields=["responses"])
                raise e

        payload = BasalamProductPayloadBuilder.build(self.product)
        product_name = payload.get("name")
        print(f"Creating product for Vendor {self.product.vendor_id} ...")
        response = self.client.post(
            url=f"/v1/vendors/{self.product.vendor_id}/products",
            json=payload
        )

        try:
            data = response.json()
        except Exception:
            data = {"raw": response.text}

        self.product.responses["create"] = {
            "status_code": response.status_code,
            "data": data,
        }

        if response.status_code == 422:
            msgs = data.get("messages") or []
            is_dup_name = any("name" in (m.get("fields") or []) for m in msgs)

            if is_dup_name and product_name:
                found_id = self._find_bsp_id_by_name(int(self.product.vendor_id), product_name)
                if found_id:
                    self.product.bsp_id = int(found_id)
                    self.product.save(update_fields=["bsp_id", "responses"])
                    print(f"Linked existing Basalam product. bsp_id={self.product.bsp_id}")
                    return self.product

        if response.status_code in (200, 201):
            print("Product Created Successfully!")
            self.product.bsp_id = data.get("id")
            self.product.bs_status = 2976    # published
            self.product.save(update_fields=["bsp_id", "bs_status", "responses"])
            return self.product

        print(f"Failed: {response.status_code}")
        self.product.bs_status = 4184    # illegal
        self.product.save(update_fields=["bs_status", "responses"])


        print("STATUS:", response.status_code)
        print("HEADERS:", response.headers)
        print("TEXT:", repr(response.text))
        print("CONTENT:", repr(response.content))
        raise Exception(f"Basalam product create failed [{response.status_code}]: {response.text}")
    
    def _find_bsp_id_by_name(self, vendor_id: int, name: str):
        page = 1
        per_page = 50

        while page <= 20:
            resp = self.client.get(
                f"/v1/vendors/{vendor_id}/products",
                params={"page": page, "per_page": per_page, "status": 3568},
            )
            if resp.status_code != 200:
                return None

            data = resp.json() or {}
            items = data.get("data", [])
            for item in items:
                if item.get("name") == name:
                    return item.get("id")

            total_page = data.get("total_page")
            if total_page and page >= int(total_page):
                break
            if not items:
                break

            page += 1

        return None
