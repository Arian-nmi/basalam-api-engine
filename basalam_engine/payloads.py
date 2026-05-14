class BasalamProductPayloadBuilder:
    @staticmethod
    def build(product):
        more = product.more_info or {}
        photos = more.get("photos") or []
        if not isinstance(photos, list) or len(photos) == 0:
            raise ValueError("BasalamProduct.more_info['photos'] is empty")

        file_ids = [int(p["file_id"]) for p in photos if isinstance(p, dict) and p.get("file_id")]
        if not file_ids:
            raise ValueError("BasalamProduct has no uploaded photos (file_id missing)")

        main = next(
            (p for p in photos
             if isinstance(p, dict) and int(p.get("order", 0)) == 0 and p.get("file_id")),
            None
        )
        main_file_id = int(main["file_id"]) if main else file_ids[0]

        variants = product.variants.all()
        if not variants.exists():
            raise ValueError("BasalamProduct has no variants")

        first_variant = variants.first()

        variant_payloads = []
        seen_signatures = set()

        for v in variants:
            color_value = (
                getattr(v.color, "visual_color_name", None)
                or getattr(v.color, "color_name", None)
                or "تک‌ رنگ"
            )
            size_value = getattr(v.size, "name", None) or "تک‌ سایز"

            props = [
                {"property": "رنگ", "value": str(color_value)},
                {"property": "سایز", "value": str(size_value)},
            ]

            if isinstance(v.properties, list):
                for p in v.properties:
                    if isinstance(p, dict) and "property" in p and "value" in p:
                        props.append({"property": str(p["property"]), "value": str(p["value"])})

            signature = tuple(sorted((p["property"], p["value"]) for p in props))
            if signature in seen_signatures:
                raise ValueError(f"Duplicate variant detected locally. sku={v.sku} props={props}")
            seen_signatures.add(signature)

            variant_payloads.append({
                "primary_price": int(v.primary_price or 0),
                "stock": 4,   # int(v.stock or 4)
                "sku": v.sku or f"SKU-{v.id}",
                "properties": props,
            })

        return {
            "name": product.bsp_name,
            "brief": product.brief or "",
            "description": product.description or "",
            "category_id": product.category_id,
            "status": 3568,     # waiting_for_confirm
            "preparation_days": product.preparation_days,
            "photo": main_file_id,
            "photos": file_ids,
            "weight": int(first_variant.weight or 0),
            "package_weight": int(first_variant.package_weight),
            "unit_type": product.unit_type,
            "unit_quantity": 1,
            "variants": variant_payloads,
        }
