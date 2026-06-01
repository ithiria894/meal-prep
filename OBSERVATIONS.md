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

---

# Session 2 Observations — 2026-05-31

又一次真實使用（Nicole 一邊煮飯一邊整理買嘢清單）。下面每條都係今次實際 friction。

## 新需求（從真實使用）

### P0 — 影響每次買嘢決定
- [ ] **每樣食材標「邊間鋪買最抵」** — 今次最大發現：同一樣嘢 T&T vs Walmart 價/貨差好遠。
  - 亞洲嘢（蒜蓉、小米辣、豆瓣醬、乾冬菇、蝦米、火鍋肉片、臘腸、Bibigo wonton）→ T&T 先齊先平
  - 西式平貨（生粉、罐頭番茄、罐頭吞拿魚、冷凍蝦仁、筷子、抹布）→ Walmart Great Value 平
  - 需要：Food.preferred_store + reason，買嘢清單自動分區（T&T list / Walmart list）
- [ ] **「我已經有」快速標記** — Nicole 成日講「粉絲我有」「蠔油我有」「XO醬我有」。買嘢清單要識跳過。
  - 現有 shopping_aggregator 有 deduct pantry，但要 stock_entry 入咗先得。現實係佢「知道有」但冇 log。
  - 需要：一鍵「我有呢樣」（唔使填數量/到期），shopping list 即跳過。

### P1 — 重要
- [ ] **長放 vs 易壞分類** — Nicole 明確分：罐頭/醬料/乾貨（可囤）vs 新鮮菜肉（買少量、2-3日份）。
  - 需要 Food.is_shelf_stable flag 驅動「呢樣可以囤、嗰樣唔好囤」建議。
- [ ] **萬用醬 → 一醬代多材料（ingredient substitution）** — Nicole 發現 XO醬 = 蒜+蝦米+辣+乾貝，可代蒜蓉+小米辣。
  - 需要 RecipeIngredient.substitutes（「冇蒜蓉？用 XO醬」），減少買嘢。呼應 rule「minimize unique items」。
- [ ] **怕辣 / 口味調整（可食但要少）** — Nicole「XO醬怕太辣」「小米辣買細樽落少少」。
  - 現有 user_disliked_foods 係硬 filter（完全唔食）。需要 spice_level / 份量 preference（可食但調低）。

## 今次揪到嘅 BUG（架構問題，建 feature 前先修）
- [x] **Bug 1（crash）**：plan.py 寫 MealPlanEntry(is_batch_cook=...)，但 model 冇呢個 column → POST /plans 一 call TypeError。✅ 2026-05-31 已修
- [x] **Bug 2（靜默錯數）**：consume_fifo 喺 entry.unit_id != unit_id 時唔做單位換算，直接當數扣 → 庫存靜靜雞錯。✅ 2026-05-31 已修

## 新 Key User Insights（補充 Session 1）
11. **「邊度買平啲」係核心決策** — 唔係買咩，係喺邊間鋪買。亞洲 vs 西式超市要分開
12. **「我有嗰樣」要好快標** — 唔肯定就唔會煮，要降低 log inventory 嘅 friction
13. **怕辣** — 辣嘢要可調（細樽、落少少），唔係全部唔食
14. **萬用醬係懶人恩物** — XO醬/老乾媽一樽代多樣，鍾意「一樽搞掂」
15. **長放嘢一次買齊，鮮嘢買少量** — 囤貨策略要 app 識分
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
