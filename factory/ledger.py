"""Ledger: per-sale unit economics and real sales totals from Printify orders."""


def unit_economics(price, cfg):
    """What one sale actually leaves you after Etsy + Printify. Assumes free shipping baked into price."""
    fees = cfg["etsy"]
    listing = fees["listing_fee"]
    transaction = price * fees["transaction_pct"]
    processing = price * fees["processing_pct"] + fees["processing_flat"]
    offsite = price * fees["offsite_ads_pct"] * fees["offsite_ads_share"]
    production = cfg["printify"]["base_cost"] + cfg["printify"]["shipping"]
    profit = price - listing - transaction - processing - offsite - production
    return {
        "price": round(price, 2),
        "etsy_fees": round(listing + transaction + processing + offsite, 2),
        "production": round(production, 2),
        "profit": round(profit, 2),
        "margin": round(profit / price, 3) if price else 0,
    }


def summarize_orders(orders, cfg):
    """Rough totals from Printify order objects (amounts are in cents)."""
    n, retail, cost = 0, 0.0, 0.0
    for o in orders:
        if o.get("status") in ("canceled", "cancelled"):
            continue
        n += 1
        for li in o.get("line_items", []):
            qty = li.get("quantity", 1)
            retail += (li.get("metadata", {}).get("price") or 0) * qty / 100
            cost += ((li.get("cost") or 0) + (li.get("shipping_cost") or 0)) / 100
    fees = cfg["etsy"]
    etsy = retail * (fees["transaction_pct"] + fees["processing_pct"]) + n * (fees["processing_flat"] + fees["listing_fee"])
    return {
        "orders": n,
        "revenue": round(retail, 2),
        "production": round(cost, 2),
        "etsy_fees_est": round(etsy, 2),
        "profit_est": round(retail - cost - etsy, 2),
    }
