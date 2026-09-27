#!/usr/bin/env python3
"""Etsy print-on-demand factory.

  python factory/factory.py run [--count N] [--demo] [--publish]   ideas -> designs -> Printify drafts
  python factory/factory.py publish ID [ID ...] | --all             push reviewed drafts live to Etsy
  python factory/factory.py sync                                    pull Printify orders into the ledger
  python factory/factory.py catalog [search]                        find blueprint / provider / variant ids
  python factory/factory.py dashboard                               rebuild dashboard.html
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import forge  # noqa: E402
import ledger  # noqa: E402
import scout  # noqa: E402

STATE = HERE / "state.json"
DESIGNS = HERE / "output" / "designs"
DASHBOARD = HERE / "dashboard.html"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def load_cfg():
    return json.loads((HERE / "config.json").read_text())


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"products": [], "log": [], "sales": None}


def save_state(state):
    state["log"] = state["log"][-200:]
    STATE.write_text(json.dumps(state, indent=1))


def log(state, agent, msg):
    print(f"[{agent}] {msg}")
    state["log"].append({"t": now(), "agent": agent, "msg": msg})


def printify_ready():
    return bool(os.environ.get("PRINTIFY_API_TOKEN") and os.environ.get("PRINTIFY_SHOP_ID"))


def cmd_run(args):
    cfg, state = load_cfg(), load_state()
    count = args.count or cfg["daily_count"]
    titles = [p["title"] for p in state["products"]]

    log(state, "SCOUT", f"researching {count} concepts{' (demo mode)' if args.demo else ''}")
    concepts = scout.generate(count, titles, demo=args.demo)

    relay = None
    if printify_ready() and not args.demo:
        from printify import Printify
        relay = Printify()
    else:
        log(state, "RELAY", "no PRINTIFY_API_TOKEN/PRINTIFY_SHOP_ID, keeping designs local")

    for c in concepts:
        pid = f"p{len(state['products']) + 1:04d}"
        path = forge.render(c, DESIGNS / f"{pid}.png", seed=pid)
        econ = ledger.unit_economics(c["price"], cfg)
        product = {
            "id": pid, "created": now(), **c,
            "design": str(path.relative_to(HERE)), "thumb": forge.thumbnail(path),
            "status": "designed", "printify_id": None, "unit": econ,
        }
        log(state, "FORGE", f"{pid} rendered \"{' '.join(c['lines'])}\" for {c['niche']}")
        if relay:
            try:
                image_id = relay.upload(path)
                product["printify_id"] = relay.create_product(product, image_id, cfg)
                product["status"] = "draft"
                log(state, "RELAY", f"{pid} draft created on Printify ({product['printify_id']})")
                if args.publish:
                    relay.publish(product["printify_id"])
                    product["status"] = "published"
                    log(state, "RELAY", f"{pid} published to Etsy")
            except Exception as e:  # keep the batch going; the product stays local
                log(state, "RELAY", f"{pid} failed: {e}")
        state["products"].append(product)
        log(state, "LEDGER", f"{pid} ${econ['price']} -> ${econ['profit']} profit/sale ({econ['margin']:.0%})")

    save_state(state)
    build_dashboard(state, cfg)


def cmd_publish(args):
    from printify import Printify
    state, relay = load_state(), Printify()
    targets = [p for p in state["products"] if p["status"] == "draft" and (args.all or p["id"] in args.ids)]
    if not targets:
        print("Nothing to publish (only products with status 'draft' can be published).")
    for p in targets:
        relay.publish(p["printify_id"])
        p["status"] = "published"
        log(state, "RELAY", f"{p['id']} published to Etsy")
    save_state(state)
    build_dashboard(state, load_cfg())


def cmd_sync(args):
    from printify import Printify
    cfg, state = load_cfg(), load_state()
    state["sales"] = {**ledger.summarize_orders(Printify().orders(), cfg), "synced": now()}
    s = state["sales"]
    log(state, "LEDGER", f"synced {s['orders']} orders, ${s['revenue']} revenue, ~${s['profit_est']} profit")
    save_state(state)
    build_dashboard(state, cfg)


def cmd_catalog(args):
    from printify import Printify
    relay, cfg = Printify(), load_cfg()
    if args.search:
        for b in relay.blueprints():
            if args.search.lower() in (b["title"] + " " + b.get("brand", "") + " " + b.get("model", "")).lower():
                print(f"blueprint {b['id']:>5}  {b['brand']} {b['model']}  {b['title']}")
        return
    print(f"Shops: {relay.shops()}")
    print(f"\nProviders for blueprint {cfg['blueprint_id']}:")
    for p in relay.providers(cfg["blueprint_id"]):
        print(f"  provider {p['id']:>4}  {p['title']}")
    colors = sorted({v["options"].get("color") for v in relay.variants(cfg["blueprint_id"], cfg["print_provider_id"])})
    print(f"\nColors from provider {cfg['print_provider_id']}: {', '.join(colors)}")


def build_dashboard(state, cfg):
    template = (HERE / "dashboard_template.html").read_text()
    payload = json.dumps({"state": state, "cfg": cfg, "built": now()}).replace("</", "<\\/")
    DASHBOARD.write_text(template.replace("/*__DATA__*/null", payload))
    print(f"dashboard -> {DASHBOARD}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--count", type=int)
    r.add_argument("--demo", action="store_true", help="offline sample ideas, no API calls")
    r.add_argument("--publish", action="store_true", help="publish straight to Etsy (skips your review)")
    p = sub.add_parser("publish")
    p.add_argument("ids", nargs="*")
    p.add_argument("--all", action="store_true")
    sub.add_parser("sync")
    c = sub.add_parser("catalog")
    c.add_argument("search", nargs="?")
    sub.add_parser("dashboard")
    args = ap.parse_args()
    {"run": cmd_run, "publish": cmd_publish, "sync": cmd_sync, "catalog": cmd_catalog,
     "dashboard": lambda a: build_dashboard(load_state(), load_cfg())}[args.cmd](args)


if __name__ == "__main__":
    main()
