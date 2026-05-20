# Meal Prep Planner — Data Model v2

Based on real usage from session 2026-05-19. Every change here comes from actual friction encountered while planning a real week of meals.

---

## What Changed from v1 and Why

| # | Change | Why |
|---|--------|-----|
| 1 | Recipe.type (main/side/snack) | 湯唔係正餐，係零食/配菜，唔應該佔 meal plan slot |
| 2 | Recipe.freeze_method | 有兩種 freeze：煮完入 Souper Cube vs 生料入 ziplock dump bag |
| 3 | Recipe.freeze_components | 意粉醬同意粉要分開 freeze（一齊雪會發脹） |
| 4 | MealPlanEntry 只放 main | Side/snack 獨立 track，唔綁 meal plan |
| 5 | MealPlanEntry 可以留空 | 有幾餐出街食/叫外賣 |
| 6 | FreezerPortion.portion_type | 區分 Souper Cube (cooked) vs Dump Bag (raw) |
| 7 | FreezerPortion 可以 fill 未來 meal plan | Freezer bank: deposit → withdraw |
| 8 | Food.is_prepackaged_frozen | 冷凍薯餅/餃子/雞塊，買返嚟就係庫存，唔使自己煮 |
| 9 | UserPreferences model | 唔食蔥蒜洋蔥、偏好低碳、煮嘢新手 |
| 10 | Staple auto-skip in shopping list | is_staple=True 嘅嘢永遠唔入購物清單 |
| 11 | Unit matching for staples | Staple 唔理 unit，有就 skip |
| 12 | Recipe servings_per_batch + eat_now + freeze_rest | 煮 6 份，食 2 份，freeze 4 份 |

---

## Revised Models

### Recipe

```
Recipe
  id, name, slug, source_url
  servings               -- 一個 recipe 出幾多份
  prep_time, cook_time

  # NEW
  type                   -- main / side / snack
  freeze_method          -- souper_cube / dump_bag / not_freezable / pre_frozen
  freeze_shelf_life_days -- 雪幾耐
  freeze_notes           -- e.g. "醬同粉分開 freeze"
  is_builtin (bool)
```

### RecipeComponent（NEW — 處理「醬同粉分開」）

```
RecipeComponent
  id, recipe_id
  name                   -- e.g. "肉醬", "意粉"
  freeze_separately (bool) -- 要唔要分開 freeze
  ingredients[]          -- 呢個 component 嘅食材
```

例如「肉醬意粉」有兩個 components：
- Component "肉醬": 牛肉碎, 罐頭番茄, 番茄醬 → freeze_separately=True
- Component "意粉": 意粉 → freeze_separately=True
煮嗰陣分開煮，freeze 分開入 cube，食嗰陣先撈埋。

簡單餸（番茄炒蛋）只有一個 component，freeze_separately=False。

### RecipeIngredient

```
RecipeIngredient
  id, recipe_id
  component_id → RecipeComponent (nullable, for simple recipes)
  food_id → Food
  unit_id → Unit
  quantity (float)
  note
  original_text
  position
```

### MealPlan

```
MealPlan
  id, week_start_date, name

MealPlanEntry
  id, meal_plan_id
  date
  meal_type (lunch/dinner)

  # Main dish — pick ONE:
  recipe_id → Recipe (nullable)              -- 自己煮
  freezer_portion_id → FreezerPortion (nullable) -- 從 freezer bank 攞
  is_eating_out (bool, default false)        -- 出街食

  servings_wanted          -- 幾多份（只適用於 recipe_id）
```

Side dishes / snacks 唔入 meal plan，獨立 track。

### BatchCookPlan（NEW — 週末煮嘢計劃）

```
BatchCookPlan
  id, meal_plan_id, date  -- 通常係週末

BatchCookEntry
  id, batch_cook_plan_id
  recipe_id
  total_servings           -- 總共煮幾多份
  eat_now_servings         -- 今個禮拜食幾多份
  freeze_servings          -- freeze 幾多份
  -- constraint: eat_now + freeze = total
```

例如：
- 肉醬意粉: total=6, eat_now=2, freeze=4
- 番茄炒蛋: total=4, eat_now=2, freeze=2

### FreezerPortion（Revised — Freezer Bank）

```
FreezerPortion
  id, recipe_id, recipe_name

  # NEW
  portion_type             -- souper_cube / dump_bag / pre_frozen
  component_name           -- e.g. "肉醬" (如果 recipe 有 components 分開 freeze)

  cube_count               -- 幾多份/包
  consumed_count
  date_prepared
  best_before_date
  location_id
  cost_per_cube

  # Dump bag specific
  cooking_instructions     -- "滾水倒入煮10分鐘" (dump bag 先需要)
```

### Food（Revised）

```
Food
  id, name, plural_name
  category_id → FoodCategory
  default_unit_id → Unit
  default_shelf_life_days
  freezer_shelf_life_days
  is_staple (bool)           -- 長期調味料，唔入購物清單
  is_prepackaged_frozen (bool) -- NEW: 冷凍薯餅/餃子，買咗直接入 freezer
```

### UserPreferences（NEW）

```
UserPreferences
  id, user_id

  # 口味
  disliked_foods[]         -- food_ids: 蔥, 蒜, 洋蔥
  dietary_tags[]           -- "low_carb", "no_spicy", etc.

  # 習慣
  meals_per_week           -- 一個禮拜幾多餐自煮（e.g. 10，其餘出街）
  max_same_dish_per_week   -- 同一款餸最多食幾餐（e.g. 2-3）
  cooking_skill_level      -- beginner / intermediate / advanced

  # Meal plan defaults
  default_batch_cook_day   -- 週末（Saturday）
```

### Store + Pricing（唔變）

```
Store
  id, name, type

FoodPrice
  id, food_id, store_id
  price, unit_size, unit_id
  date_recorded, on_sale
```

---

## Revised Pipelines

### Pipeline 1: 週計劃 → 購物清單

```
User sets:
  呢個禮拜要食乜 main (max 2-3 each)
  + 週末 batch cook 清單 (eat_now + freeze)
  + side/snack 另外 track

    ↓
Aggregate ingredients:
  from batch_cook_entries (total_servings, 唔係 eat_now)
  + from side/snack 想整嘅份數
    ↓
Skip staples (is_staple=True, 唔理 unit match)
    ↓
Skip disliked_foods (from UserPreferences)
    ↓  
Deduct pantry stock (FIFO)
    ↓
Output shopping list
  + 加埋要買嘅 pre_frozen items（薯餅、餃子）
```

### Pipeline 2: Batch Cook → Freeze

```
週末：
  煮肉醬意粉 6 份
    → component "肉醬" → 4 份入 Souper Cubes (FreezerPortion type=souper_cube)
    → component "意粉" → 另外煮，freeze 4 份
    → eat 2 份

  整 dump bags:
    → 小火鍋包 ×4 → 入 ziplock (FreezerPortion type=dump_bag)
    → cooking_instructions = "滾水+火鍋湯底，倒入煮10分鐘"

  Deduct stock (FIFO)
  Log to StockLog
```

### Pipeline 3: 下個禮拜 Plan → Withdraw from Freezer

```
Plan 下個禮拜：
  → System shows: "你 freezer 有: 肉醬×4, 番茄炒蛋×2, 小火鍋包×4..."
  → User picks: 星期一 lunch = 肉醬意粉 (from freezer)
  → FreezerPortion.consumed_count += 1
  → 只需要補煮少量新嘢
```

### Pipeline 4: Smart Suggestion（考慮 preferences）

```
Score recipes:
  + expiring pantry items
  + freezer items near expiry
  - contains disliked_foods (hard filter, 直接排除)
  - exceeds max_same_dish_per_week
  - too complex for cooking_skill_level
  × freeze_method bonus (can batch cook)
```

---

## Shopping List Changes

```
ShoppingListItem
  id, shopping_list_id
  food_id, unit_id, quantity
  checked (bool)
  category_id
  estimated_cost, store_id
  pantry_deducted (float)

  # NEW
  source_type              -- batch_cook / side / pre_frozen_buy
  source_recipe_id         -- 邊個餸需要
```

Staple logic:
- if food.is_staple == True → SKIP entirely（唔理 unit match）
- if food in user.disliked_foods → WARN（食譜用咗你唔食嘅嘢）

---

## Key Insight: The Flywheel

```
Week 1: Cook 5 dishes → eat 10, freeze 8        (buy a lot)
Week 2: Cook 3 dishes → eat 6, freeze 4          (buy less, withdraw 8 from freezer)
         + withdraw 4 from freezer
Week 3: Cook 2 dishes → eat 4, freeze 2          (buy even less)
         + withdraw 6 from freezer
Week 4: Cook 2 dishes, withdraw 8 from freezer   (minimal shopping)

Freezer bank grows → shopping shrinks → cooking time shrinks
```

This is the core value prop: the app gets EASIER every week you use it.
