# Etsy Factory

My version of the "AI factory" TikTok setup: an Etsy print-on-demand shirt shop where agents come up with products, make the designs, and list them.

```
SCOUT (Claude)  ->  FORGE (Pillow)  ->  RELAY (Printify API)  ->  Etsy listing  ->  LEDGER (profit)
niche + phrase      print-ready PNG     draft product              via Printify's       real orders,
+ title/tags/copy   4500x5400           you review, then publish   Etsy integration     fees, margin
```

Printify prints and ships each shirt only after someone orders it, so there's no inventory. Printify's Etsy integration turns a published product into an Etsy listing, so you don't need Etsy API access.

## Try it (no accounts needed)

```bash
pip install -r factory/requirements.txt
python factory/factory.py run --demo --count 6
open factory/dashboard.html
```

## Make it real

1. **Etsy**: open a shop (listing fee is $0.20 per item).
2. **Printify**: make a free account, then connect it to your Etsy shop under *Manage stores*. Under *My profile > Connections*, create an API token.
3. **Claude API key**: from console.anthropic.com. It costs a few cents per batch of ideas.
4. Set the keys:
   ```bash
   export ANTHROPIC_API_KEY=...
   export PRINTIFY_API_TOKEN=...
   python factory/factory.py catalog            # prints your shop id + available colors
   export PRINTIFY_SHOP_ID=...
   ```
5. Check `config.json`. The default shirt is a Bella+Canvas 3001 (blueprint 12) from provider 29 in white and natural. `catalog "3001"` or `catalog "hoodie"` lists other blueprints.
6. Run it:
   ```bash
   python factory/factory.py run               # 3 new products, created as Printify drafts
   # look them over in Printify or the dashboard, then:
   python factory/factory.py publish p0001 p0003   # or --all
   python factory/factory.py sync              # pull orders and update profit in the dashboard
   ```

### On autopilot

`.github/workflows/factory.yml` runs every day and creates new drafts. It does nothing until you add `ANTHROPIC_API_KEY`, `PRINTIFY_API_TOKEN` and `PRINTIFY_SHOP_ID` as repo secrets (Settings > Secrets and variables > Actions). Scheduled runs only fire from the default branch. It creates **drafts** on purpose. `run --publish` skips the review step, but a single trademarked phrase can get the whole Etsy shop suspended, so look at each design first.

## The money, honestly

At $26 a shirt: Etsy takes about $3.30 in fees and Printify charges about $16.25 for the shirt plus shipping. That leaves **about $6.40 profit per sale (around 25%)**. The dashboard has a calculator for this.

The video's shop showed **56.2K visits, 210 orders, 0.3% conversion and about $7.6K revenue**. After fees and production costs, that's roughly **$1.5–2K of profit**. That's real money, but it's not the number on screen. And the flashy pixel-art dashboard didn't cause any of it. What did:

- **Volume.** Most listings never sell. Shops that make money have hundreds of listings.
- **Niche and SEO.** Specific buyer, phrase they'd say themselves, titles and tags that match what people search. Scout's prompt is built around this.
- **Photos.** Real lifestyle mockups (like the girl-in-the-tee shot in the video) convert way better than flat designs. Printify generates mockups; nicer ones are worth it.
- **Time.** New Etsy shops get little traffic for the first couple of months.

Other rules: Etsy requires you to disclose Printify as your production partner (the listing copy already mentions it), and you should never copy brands, characters, lyrics, or quotes. Also, Etsy profit is taxable income. Keep the ledger.

## Upgrades worth doing

- Add image-generation designs (illustrations, like the dog and coffee art in the video) next to the text ones.
- Add a winners report: sync orders by product, then have Scout make variations of whatever sells.
- Try more products (hoodies, mugs, tote bags) using the same pipeline with a different `blueprint_id`.

Fonts (Abril Fatface, Bebas Neue, Pacifico) are from Google Fonts under the SIL Open Font License and are fine to use on products you sell.
