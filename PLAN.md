# Meal Prep Planner — Architecture Plan

## Context

Nicole 住溫哥華，自己煮飯嘅痛點：每日諗食乜、材料唔夠、買完用唔晒就爛。想做一個 DIY HelloFresh — 週末 batch cook，Souper Cubes 分裝雪藏，平日翻熱食。

市場研究結論：冇任何現有 app 同時做到 batch cook planning + freezer portion tracking + pantry expiry + shopping list aggregate + cost tracking。7 個開源 repo 有好多可以借嘅 pattern。

**設計原則：AI 用量 minimize。** 用戶手動揀餸 = 零 API call。只有 YouTube import 同 auto-plan 先用 AI。

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | Python + FastAPI | 同 Mealie 一樣，可以直接借 model patterns |
| Database | SQLite (MVP) → PostgreSQL (later) | 簡單開始，Grocy 都係 SQLite |
| ORM | SQLAlchemy + Alembic | 同 Mealie，model 可以幾乎 copy |
| Recipe Parser | recipe-scrapers (Python lib) | Tandoor 用緊，600+ sites，免費 |
| Video Import | yt-dlp + Groq Whisper | Norish 嘅 pattern，Groq 最平（$0.02/hr） |
| Frontend | Web UI (Phase 4) | MVP 先用 CLI |
| AI (minimal) | LiteLLM | Tandoor 嘅 pattern，支援所有 provider |

---

## Data Models

### 食材系統（借 Mealie 三層 model）

```
Food
  id, name, plural_name
  aliases[]                    -- 「蛋」=「雞蛋」=「egg」
  category_id → FoodCategory   -- 超市分類（蔬果、肉、調味）
  default_unit_id → Unit
  default_shelf_life_days      -- 雪櫃保質期
  freezer_shelf_life_days      -- 冷凍保質期
  is_staple (bool)             -- 長期品（豉油、鹽）

Unit
  id, name, abbreviation
  aliases[]                    -- 「g」=「gram」=「克」
  standard_quantity, standard_unit  -- 標準化（1 tbsp = 15 ml）

FoodCategory
  id, name, sort_order         -- 超市 aisle 排序
```

### 庫存系統（借 Grocy stock batch model）

```
Location
  id, name, type (fridge/freezer/pantry/shelf)

StockEntry
  id, food_id, location_id
  amount, unit_id
  best_before_date
  purchased_date
  price, store_id              -- 買入價
  batch_id                     -- FIFO 用

StockLog
  id, food_id, amount, unit_id
  transaction_type (purchase/consume/spoil/transfer)
  related_recipe_id            -- 邊個餸用咗
  timestamp
```

### Freezer Portion（全新，冇人做過）

```
FreezerPortion
  id, recipe_id, recipe_name
  cube_count                   -- 幾多舊 Souper Cube
  date_prepared
  best_before_date             -- = date_prepared + recipe.freezer_shelf_life_days
  location_id                  -- 邊個 freezer
  consumed_count               -- 食咗幾多舊
  cost_per_cube                -- 每舊幾錢
```

### 食譜系統（借 Tandoor model）

```
Recipe
  id, name, slug, source_url
  servings, servings_text
  prep_time, cook_time
  freezable (bool)
  freezer_shelf_life_days
  is_builtin (bool)

RecipeIngredient
  id, recipe_id
  food_id → Food
  unit_id → Unit
  quantity (float)
  note                         -- 「切粒」、「室溫」
  original_text                -- AI parse 前嘅 raw text
  position

RecipeStep
  id, recipe_id, position, text, duration_minutes
```

### Meal Plan

```
MealPlan
  id, week_start_date, name

MealPlanEntry
  id, meal_plan_id
  recipe_id
  portions                     -- 要幾多份
  is_batch_cook (bool)         -- 一次過煮定逐餐煮
```

### Shopping List

```
ShoppingList
  id, meal_plan_id, created_at, status (draft/shopping/done)

ShoppingListItem
  id, shopping_list_id
  food_id, unit_id, quantity
  checked (bool)
  category_id → FoodCategory   -- aisle 排序
  estimated_cost
  store_id                     -- 去邊買
  recipe_sources[]             -- 邊幾個 recipe 需要呢樣嘢（Mealie pattern）
  pantry_deducted (float)      -- 扣咗幾多 pantry stock
```

### Store + Pricing（全新 generic system）

```
Store
  id, name, type (supermarket/wholesale/online/market)

FoodPrice
  id, food_id, store_id
  price, currency
  unit_size, unit_id           -- $5.99 per 12 隻
  date_recorded
  on_sale (bool)
  → computed: unit_cost = price / unit_size
```

---

## Core Pipelines（全部 deterministic，零 AI）

### Pipeline 1: 週 Plan → Shopping List

```
User picks: [蛋炒飯×3, 番茄蛋湯×2, 照燒雞×3]
    ↓
Aggregate ingredients across all recipes:
  蛋: 蛋炒飯(3×2隻) + 番茄蛋湯(2×3隻) = 12隻
  蔥: 蛋炒飯(3×2條) + 番茄蛋湯(2×1條) = 8條
  雞髀: 照燒雞(3×4件) = 12件
    ↓
Unit conversion (BFS graph, from Tandoor):
  如果一個 recipe 用「2 cup 麵粉」另一個用「200g 麵粉」
  → convert to same unit → 合併
    ↓
Deduct pantry stock (from Grocy model):
  pantry 有 4 隻蛋 → 購物清單只需要 8 隻
  pantry 有豉油(staple) → 唔入清單
    ↓
Cost estimation:
  per store: T&T total $45, Costco total $38
    ↓
Group by FoodCategory (aisle sort):
  蔬果: 蔥×8, 番茄×6
  肉類: 雞髀×12
  蛋奶: 蛋×8
```

### Pipeline 2: Cook → Freeze

```
User marks "照燒雞" as cooked (batch of 3 portions)
    ↓
Create FreezerPortion:
  recipe=照燒雞, cube_count=3
  date_prepared=today
  best_before=today + 14 days
  cost_per_cube = total_ingredient_cost / 3
    ↓
Deduct ingredients from StockEntry (FIFO):
  consume 12 件雞髀 (oldest batch first)
  consume 醬油、薑、蒜 (amounts per recipe × 3)
    ↓
Log to StockLog (audit trail)
```

### Pipeline 3: Expiry → Recipe Suggestion（deterministic scoring）

```
Cron check: 番茄 expires in 2 days, 蔥 expires in 3 days
    ↓
Query recipes containing 番茄 OR 蔥
    ↓
Score each recipe:
  +10 per expiring ingredient used
  +5 per pantry ingredient already available
  -3 per new ingredient needed to buy
  -2 if cooked within last 3 days (variety)
  ×1.5 if freezable (can batch cook)
    ↓
Return ranked list: "番茄蛋湯 (score 28), 番茄炒蛋 (score 25)..."
```

### Pipeline 4: Cross-Recipe Optimization（deterministic greedy）

```
User wants 8 portions for the week, has these recipes saved:
    ↓
Build ingredient overlap matrix:
  蛋炒飯 ∩ 番茄蛋湯 = {蛋, 蔥}        overlap=2
  蛋炒飯 ∩ 照燒雞   = {蔥, 蒜}        overlap=2
  番茄蛋湯 ∩ 親子丼  = {蛋, 蔥}        overlap=2
  照燒雞 ∩ 親子丼    = {雞, 蔥}         overlap=2
    ↓
Greedy selection:
  1. Pick highest-rated recipe → 蛋炒飯
  2. Pick recipe with most overlap with selected → 番茄蛋湯 (+蛋,蔥)
  3. Pick next best overlap → 照燒雞 (+蔥,蒜)
  4. Pick next → 親子丼 (+雞,蛋,蔥)
    ↓
Constraints check:
  - 唔好 >50% 同一蛋白質來源 ✓
  - Budget 範圍內 ✓
  - 包含用戶 preference ✓
    ↓
Output: 蛋炒飯×2, 番茄蛋湯×2, 照燒雞×2, 親子丼×2
Total unique ingredients: 8 (vs 15+ if random selection)
```

---

## AI Usage（只有兩個地方）

| Feature | AI? | Provider | Est. Cost |
|---------|-----|----------|-----------|
| YouTube recipe import | Yes | yt-dlp 字幕(free) → Groq Whisper($0.02/hr) → Claude parse | ~$0.01/recipe |
| Auto meal plan (optional) | Maybe | Claude/GPT for natural language preference → plan | ~$0.02/plan |
| 其他所有嘢 | No | Deterministic algorithms | $0 |

YouTube import flow (from Norish):
```
YouTube URL
  → yt-dlp download captions (FREE, 90%+ videos have captions)
  → if no captions: yt-dlp download audio → Groq Whisper transcribe ($0.02/hr)
  → caption/transcript text → recipe-scrapers or regex parse
  → if parse fails: Claude API extract recipe JSON (~$0.01)
  → structured Recipe + RecipeIngredients
```

---

## MVP Phases

### Phase 1: Core Data + CLI（零 AI）
- SQLAlchemy models + SQLite + Alembic migrations
- CLI commands: add-recipe, add-food, stock-in, stock-out
- Plan week → generate shopping list (deterministic pipeline)
- Cost tracking (manual price entry)
- **QA: 手動 plan 一個禮拜，verify shopping list 正確**

### Phase 2: Recipe Import
- recipe-scrapers for URL import (600+ sites)
- YouTube import (yt-dlp + Groq Whisper)
- Built-in recipe library (20-30 個常見可雪藏嘅中式/日式餸)
- Ingredient parser (tokenize "2 cups flour" → food + unit + quantity)
- **QA: import 10 個 URL + 5 個 YouTube，verify parse 正確**

### Phase 3: Smart Features
- Expiry alerts + deterministic recipe suggestions
- Cross-recipe ingredient overlap optimization (greedy algorithm)
- Store price comparison
- Freezer portion tracking (Souper Cubes)
- Batch cook workflow (cook → create portions → deduct stock)
- **QA: 跑完整 workflow 一個禮拜 cycle**

### Phase 4: Web UI
- FastAPI serve frontend
- Week calendar (drag-and-drop meal plan)
- Shopping list with checkboxes + store grouping
- Pantry/freezer dashboard
- Cost summary + charts

### Phase 5: Integrations
- Instacart Developer Platform API
- QR code labels for freezer portions
- Multi-user household sync

---

## Key Files to Create (Phase 1)

```
meal-prep/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py           -- SQLAlchemy base + mixins
│   │   │   ├── food.py           -- Food, Unit, FoodAlias, UnitAlias, FoodCategory
│   │   │   ├── recipe.py         -- Recipe, RecipeIngredient, RecipeStep
│   │   │   ├── stock.py          -- StockEntry, StockLog, Location, FreezerPortion
│   │   │   ├── plan.py           -- MealPlan, MealPlanEntry
│   │   │   ├── shopping.py       -- ShoppingList, ShoppingListItem
│   │   │   └── store.py          -- Store, FoodPrice
│   │   ├── services/
│   │   │   ├── shopping_aggregator.py  -- Pipeline 1: plan → shopping list
│   │   │   ├── stock_manager.py        -- FIFO consume, expiry check
│   │   │   ├── unit_converter.py       -- BFS unit conversion graph
│   │   │   ├── cost_calculator.py      -- Per-meal, per-week cost
│   │   │   └── recipe_suggester.py     -- Deterministic scoring
│   │   ├── cli.py                -- Click CLI for MVP
│   │   └── db.py                 -- DB setup
│   ├── data/
│   │   ├── builtin_recipes/      -- JSON starter recipes
│   │   ├── units.json            -- Unit conversion table
│   │   └── categories.json       -- Supermarket aisle categories
│   ├── alembic/
│   └── tests/
│       ├── test_shopping_aggregator.py
│       ├── test_stock_manager.py
│       ├── test_unit_converter.py
│       └── test_cost_calculator.py
├── pyproject.toml
└── README.md
```

---

## Reusable Code from Open Source

| What | From | File Reference |
|------|------|---------------|
| Food/Unit/Ingredient model structure | Mealie | `mealie/db/models/recipe/ingredient.py` |
| Shopping list recipe reference tracking | Mealie | `mealie/db/models/household/shopping_list.py` |
| Stock batch + FIFO + expiry schema | Grocy | `grocy/migrations/0001.sql` - `0005.sql` |
| BFS unit conversion graph | Tandoor | `recipes/cookbook/helper/unit_conversion_helper.py` |
| Recipe URL import + ingredient parser | Tandoor | `recipes/cookbook/helper/recipe_url_import.py` |
| Food alias automation system | Tandoor | `recipes/cookbook/helper/automation_helper.py` |
| YouTube processor (captions-first) | Norish | `norish/packages/api/src/video/processors/youtube.ts` |
| Multi-provider transcription | Norish | `norish/packages/api/src/ai/transcriber.ts` |
| Recurring groceries concept | Norish | `norish/packages/db/src/schema/groceries.ts` |
| recipe-scrapers library | Tandoor | Python library, pip install |

---

## Verification Plan

### Phase 1 QA Checklist
1. Create 3 recipes manually via CLI
2. Add pantry items (蛋×6, 豉油, 米)
3. Plan week: recipe_A×3, recipe_B×2, recipe_C×3
4. Generate shopping list → verify:
   - Shared ingredients aggregated correctly
   - Units converted where applicable
   - Pantry items deducted
   - Cost estimated per store
5. Mark recipe_A as "cooked" → verify:
   - FreezerPortions created
   - Stock consumed (FIFO)
   - StockLog entries created
6. Add item with expiry in 2 days → verify suggestion ranking

### E2E Happy Path
```
add-recipe "蛋炒飯" --servings 2 --ingredients "蛋 2隻, 飯 1碗, 蔥 2條"
add-recipe "番茄蛋湯" --servings 2 --ingredients "蛋 3隻, 番茄 2個, 蔥 1條"
stock-in "蛋" 4 --location freezer --expiry 2026-05-25
plan-week --recipes "蛋炒飯:3,番茄蛋湯:2"
shopping-list generate
# Expected: 蛋 8隻(need) - 4隻(have) = 4隻, 番茄 4個, 蔥 8條, 飯 3碗
cook "蛋炒飯" --portions 3
# Expected: 3 FreezerPortions created, 6蛋+3飯+6蔥 consumed from stock
```
