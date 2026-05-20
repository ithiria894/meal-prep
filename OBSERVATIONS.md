# Session 1 Observations — 2026-05-19

Real usage session with Nicole. Every observation below comes from actual friction encountered.

## Features Confirmed Working
- [x] Recipe CRUD via API
- [x] Shopping list generation (aggregate + deduct pantry + skip staples)
- [x] FIFO stock consume + deficit handling
- [x] YouTube recipe import (Whisper + GPT extract)
- [x] Image inventory scan endpoint
- [x] Budget tracking ($500/month limit)
- [x] Expense logging (grocery/eating_out/delivery categories)
- [x] T&T website browsing + add to cart via Chrome DevTools

## Features Needed (from real usage)

### P0 — Blocking daily use
- [ ] **Eating out / delivery expense tracking** — upload receipt photo, AI extract amount + store. Nicole wants to track ALL food spending, not just grocery
- [ ] **Recipe steps with YouTube link** — "開住 YouTube 跟住做" is her actual cooking workflow. Each recipe should link to the source video
- [ ] **T&T weekly specials → recipe suggestions** — scrape T&T flyer, match against recipe DB, suggest what to cook based on what's on sale
- [ ] **Grocery cart integration** — one-click add shopping list to T&T/Instacart cart. Today's manual process was painful (T&T website full of bugs, search broken)

### P1 — Important for weekly workflow
- [ ] **Meal plan → shopping cart export** — generate shopping list then export to T&T/Instacart format
- [ ] **Portion calculator for bulk buy** — "if I buy 2lb pork, how do I split across 3 recipes?"
- [ ] **Freeze instructions per recipe** — which parts freeze separately, how long, defrost method
- [ ] **Cost per meal tracking** — auto-calculate from food prices
- [ ] **Budget alert** — warn when approaching $500 limit, suggest cheaper alternatives
- [ ] **User preferences auto-apply** — filter out 蔥/蒜/洋蔥 from ALL recipe suggestions automatically

### P2 — Nice to have
- [ ] **Receipt photo → auto expense** — scan receipt, extract store + total + items
- [ ] **T&T price tracking** — record prices each week, show trends, alert when something is cheaper
- [ ] **Freezer inventory dashboard** — what's in the freezer, when does it expire, what to eat first
- [ ] **Cooking timer integration** — step-by-step cooking mode with timers
- [ ] **QR code for Souper Cube labels** — scan to see what's inside, when prepared, when expires

## Data Model Changes Needed
- [ ] Recipe.source_video_url — YouTube link for cooking along
- [ ] Expense.receipt_image — photo of receipt
- [ ] Add "eating_out" and "delivery" as first-class expense categories
- [ ] WeeklySpecials model — store promotions scraped from flyers
- [ ] RecipeComponent freeze instructions — what to freeze separately

## Key User Insights
1. **Nicole 唔識煮嘢** — recipes must be dead simple, max 5 steps
2. **唔食蔥、蒜、洋蔥** — hard filter, never suggest
3. **偏好低碳** but likes 薯蓉/薯餅 (contradictory, but real)
4. **Instant/frozen meals are valid** — 日清意粉, 叮叮懶人菜 count as meals
5. **T&T is primary store** — $59 free delivery, code FREE59
6. **$500/month budget** — includes eating out + grocery + snacks
7. **Batch cook Sunday** — cook multiple dishes, freeze in Souper Cubes
8. **2-3 max per dish per week** — variety matters
9. **"搞咁撚多" reaction** — too many ingredients = friction. Maximize reuse, minimize unique items
10. **Buy based on sales** — check T&T flyer first, THEN decide what to cook

## Architecture Insights
- T&T website search is broken (returns errors). Need to use category navigation instead
- T&T has no public API. Cart manipulation via Chrome DevTools works but is fragile
- Instacart API would be better but adds 6% + $5.99 fees
- YouTube video import needs OCR for on-screen text (Chinese recipes show ingredients as text overlay, not spoken)
- Local Whisper (tiny/base) is bad for Chinese. OpenAI Whisper API is much better ($0.01/recipe)
