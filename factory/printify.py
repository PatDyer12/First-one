"""Relay: pushes designs to Printify. Printify's Etsy integration turns a published product into an Etsy listing."""
import base64
import os

import requests

API = "https://api.printify.com/v1"


class Printify:
    def __init__(self, token=None, shop_id=None):
        self.token = token or os.environ.get("PRINTIFY_API_TOKEN")
        if not self.token:
            raise RuntimeError("Set PRINTIFY_API_TOKEN (Printify > My profile > Connections > API tokens).")
        self.shop_id = shop_id or os.environ.get("PRINTIFY_SHOP_ID")
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {self.token}", "User-Agent": "etsy-factory"})

    def _req(self, method, path, **kw):
        r = self.s.request(method, f"{API}{path}", timeout=60, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"Printify {method} {path} -> {r.status_code}: {r.text[:400]}")
        return r.json() if r.content else {}

    def shops(self):
        return self._req("GET", "/shops.json")

    def blueprints(self):
        return self._req("GET", "/catalog/blueprints.json")

    def providers(self, blueprint_id):
        return self._req("GET", f"/catalog/blueprints/{blueprint_id}/print_providers.json")

    def variants(self, blueprint_id, provider_id):
        return self._req("GET", f"/catalog/blueprints/{blueprint_id}/print_providers/{provider_id}/variants.json")["variants"]

    def upload(self, path):
        data = base64.b64encode(open(path, "rb").read()).decode()
        return self._req("POST", "/uploads/images.json", json={"file_name": os.path.basename(path), "contents": data})["id"]

    def create_product(self, product, image_id, cfg):
        """Creates a draft product. Nothing reaches Etsy until publish()."""
        colors = {c.lower() for c in cfg["shirt_colors"]}
        sizes = {s.upper() for s in cfg["sizes"]}
        chosen = [
            v for v in self.variants(cfg["blueprint_id"], cfg["print_provider_id"])
            if v["options"].get("color", "").lower() in colors and v["options"].get("size", "").upper() in sizes
        ]
        if not chosen:
            raise RuntimeError("No variants matched shirt_colors/sizes in config.json; run `factory.py catalog`.")
        price = int(round(product["price"] * 100))
        body = {
            "title": product["title"],
            "description": product["description"],
            "tags": product["tags"],
            "blueprint_id": cfg["blueprint_id"],
            "print_provider_id": cfg["print_provider_id"],
            "variants": [
                {"id": v["id"], "price": price + (300 if v["options"].get("size", "").upper() in ("2XL", "3XL") else 0), "is_enabled": True}
                for v in chosen
            ],
            "print_areas": [{
                "variant_ids": [v["id"] for v in chosen],
                "placeholders": [{"position": "front", "images": [{"id": image_id, "x": 0.5, "y": 0.5, "scale": 1, "angle": 0}]}],
            }],
        }
        return self._req("POST", f"/shops/{self.shop_id}/products.json", json=body)["id"]

    def publish(self, product_id):
        flags = {k: True for k in ("title", "description", "images", "variants", "tags", "keyFeatures", "shipping_template")}
        return self._req("POST", f"/shops/{self.shop_id}/products/{product_id}/publish.json", json=flags)

    def orders(self, pages=5):
        out = []
        for page in range(1, pages + 1):
            data = self._req("GET", f"/shops/{self.shop_id}/orders.json", params={"page": page, "limit": 50})
            out += data.get("data", [])
            if page >= data.get("last_page", 1):
                break
        return out
