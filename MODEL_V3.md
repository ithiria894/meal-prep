# Meal Prep — Model V3 設計

> 來源：Session 2 真實使用（2026-05-31，Nicole 一邊煮飯一邊整理 T&T/Walmart 買嘢清單）。
> 詳細需求見 `OBSERVATIONS.md` → Session 2。
> **狀態：設計提案，未實作。等 Nicole review。**

V2 已做嘅唔重覆。呢度淨係 V3 新增。

---

## 0. 已完成（Session 2 修咗嘅 bug）

| Bug | 修法 | Test |
|---|---|---|
| `MealPlanEntry` 缺 `is_batch_cook` → POST /plans crash | model 加返 `is_batch_cook: bool = True` | `test_bugfixes_session2.py` |
| `consume_fifo` 唔做單位換算 → 庫存靜默錯數 | 用 `unit_converter.convert()` 換算每個 batch | 同上 |

---

## 1. 🔴 P0 — 食材「邊度買最抵」

**痛點**：同一樣嘢 T&T vs Walmart 價/貨差好遠。亞洲嘢去 T&T，西式平貨去 Walmart。買嘢清單要自動分區。

### Schema
```
Food (新增欄位)
  preferred_store_id → stores.id  (nullable)   -- 建議去邊間買
  store_reason: str?                           -- "亞洲嘢T&T齊" / "Great Value平"
```

`stores` 表已存在，`food_prices(food_id, store_id, price, on_sale)` 已存在 → 已可比價。V3 只係加「建議買邊間」。

### API
```
GET /api/shopping-lists/{id}/by-store
  → 將 shopping list items 按 preferred_store 分組
  → 回傳 { "T&T": [items...], "Walmart": [items...], "未分類": [...] }
```
（純 read view，唔改現有 generate 邏輯）

### 決策邏輯（deterministic，零 AI）
1. item 有 `food.preferred_store_id` → 用佢
2. 冇 → 睇 `food_prices` 邊間最平（min unit_cost）
3. 都冇 → 落「未分類」

---

## 2. 🔴 P0 — 「我已經有」快速標記

**痛點**：Nicole 成日講「粉絲我有」「蠔油我有」。買嘢清單要識跳過，但叫佢填數量+到期日太麻煩 → 唔會做。

### 現狀
`shopping_aggregator` 已 deduct pantry stock，**但要 `stock_entries` 有 record 先得**。問題係 friction 太高。

### 方案：quick-have（唔使填數量）
```
StockEntry 已有 amount / unit_id / best_before_date 全部 nullable-friendly
新增 API：
POST /api/stock/quick-have   { food_id }
  → 建一個 StockEntry(food_id, amount=None→視為「有」, is_quick_have=True)
  → 新增欄位 StockEntry.is_quick_have: bool = False

shopping_aggregator 改：
  如果 food 有任何 is_quick_have 或 amount>0 嘅 entry → skip（當有貨）
```

### UI 概念
recipe / shopping list 每樣嘢一個「✓ 我有」掣，一撳即 quick-have，下次唔再買。

---

## 3. 🟡 P1 — 長放 vs 易壞分類

**痛點**：罐頭/醬料/乾貨可囤；新鮮菜肉買少量。app 要識分。

### Schema
```
Food (新增)
  is_shelf_stable: bool = False   -- 常溫長放（罐頭、乾貨、醬料）
```
（已有 `is_staple` 係「長期必備品」語義唔同；`is_prepackaged_frozen` 係冷凍。新 flag 專指常溫長放。）

### 用途
- 購物建議：`is_shelf_stable` → 「可一次買多啲囤」；否則「買 2-3 日份」
- 配 expiry dashboard：易壞嘢優先提醒

---

## 4. 🟡 P1 — 萬用醬代材料（substitution）

**痛點**：Nicole 發現 XO醬 = 蒜+蝦米+辣+乾貝，可代蒜蓉+小米辣。減少買嘢（呼應 rule「minimize unique items」）。

### Schema
```
FoodSubstitution (新表)
  id
  food_id → foods.id            -- 原材料（蒜蓉）
  substitute_food_id → foods.id -- 代替品（XO醬）
  note: str?                    -- "XO醬已含蒜+蝦米+辣"
  ratio: float = 1.0            -- 用量比例
```

### 用途
shopping list 生成時：如果某 food 要買，但有 substitute 喺 pantry（quick-have）→ 提示「你有 XO醬，可代蒜蓉，唔使買」。

---

## 5. 🟡 P1 — 怕辣 / 口味可調（可食但要少）

**痛點**：`user_disliked_foods` 係硬 filter（完全唔食）。但「XO醬怕太辣」「小米辣落少少」係「可食但調低」，唔係唔食。

### Schema
```
Recipe (新增)
  spice_level: int = 0          -- 0=唔辣 1=微辣 2=中辣 3=好辣

UserPreferences (新增)
  max_spice_level: int = 1      -- 接受到嘅最辣程度
```

### 用途
- auto_planner 過濾 / 警告：recipe.spice_level > user.max_spice_level → 標「⚠️ 可能太辣，落少少辣椒」
- 唔係硬 filter（唔似蔥蒜），係「提示調整份量」

---

## 實作優先次序建議

1. ✅ **P0 bug**（已修）
2. **P0-1 邊度買**：Food.preferred_store + /by-store view（影響每次買嘢）
3. **P0-2 quick-have**：最大減 friction，令 inventory 真係 work
4. **P1-3 shelf_stable**：細，順手加
5. **P1-4 substitution**：要諗 UI，稍後
6. **P1-5 spice_level**：細，順手加

## Migration 注意
- 全部新欄位有 default，舊資料唔會爛
- 新表（FoodSubstitution）獨立，唔影響現有
- `StockEntry.is_quick_have` 加 default False
- ⚠️ 用緊 SQLite，加欄位要 Alembic migration 或 recreate（MVP 階段可 drop+recreate）
