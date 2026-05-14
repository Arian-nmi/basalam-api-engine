from .client import BasalamAPIClient
from website.models import BasalamConfig


class BasalamVendorService:
    def __init__(self, client):
        self.client = client

    def get_or_fetch_vendor_id(self):
        """
        Extracts vendor information directly from the user profile (/v1/users/me).
        """
        print("calling /v1/users/me to find vendor info...")
        response = self.client.get("/v1/users/me")
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch user info [{response.status_code}]: {response.text}")
            
        user_data = response.json()
        vendor_info = user_data.get("vendor")

        if not vendor_info:
             raise Exception("No 'vendor' key found in user profile. Please create a vendor first.")

        vendor_id = vendor_info.get("id")

        if not vendor_id or vendor_id == 0:
            raise Exception(
                f"Vendor ID is 0 or invalid. \n"
                f"Vendor Data: {vendor_info} \n"
                "Please make sure your vendor is created and active in Basalam."
            )

        print(f"Found Vendor ID: {vendor_id}")
        return vendor_id


class BasalamCategoryTool:
    
    def __init__(self):
        config = BasalamConfig.objects.filter(is_active=True).first()
        if not config:
            raise RuntimeError("No active BasalamConfig found")
        self.client = BasalamAPIClient(config.v1_access_token)

    def fetch_all_categories(self):
        """
        Gets the list of main categories.
        """
        print("Fetching categories...")
        response = self.client.get("/v1/categories")
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            return

        data = response.json()
        categories = data.get("data", [])
        self._print_categories(categories)

    def _print_categories(self, categories, indent=0):
        """
        Tree view of categories to find ID
        """
        prefix = "    " * indent
        for cat in categories:
            cat_id = cat.get("id")
            title = cat.get("title")
            print(f"{prefix}[ID: {cat_id}] {title}")
            children = cat.get("children", [])
            if children:
                self._print_categories(children, indent + 1)
