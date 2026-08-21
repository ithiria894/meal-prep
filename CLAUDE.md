

---

## 由 Claude memory 搬入（2026-08-21）— `project_meal_prep.md`

原本住喺 `~/.claude/projects/-home-nicole/memory/`，每個 session 都載入。
呢啲係 project-specific，應該 cd 入呢個 repo 先 load。

---
name: Meal Prep Planner Project
description: DIY HelloFresh app for Nicole in Vancouver - batch cook + Souper Cube freeze + pantry tracking + budget
type: project
originSessionId: 1d13e80d-dd48-4621-bdc1-440aa4665a71
---
Nicole 嘅 meal prep planner side project。代碼喺 `~/MyGithub/meal-prep/`。

**狀態：** Trial month（2026-05 開始），backend API 已 work，試用一個月再 finalize

**Tech stack：** Python FastAPI + SQLite + Expo React Native (frontend 未開始)

**核心文件：**
- `MODEL_V2.md` — 最新 data model
- `OBSERVATIONS.md` — session 1 嘅所有 feature 需求
- `PLAN.md` — architecture plan

**Nicole 嘅 preferences：**
- 唔食蔥、蒜、洋蔥
- 唔識煮嘢，要簡單食譜（max 5 步）
- 用 Souper Cubes freeze 所有餸
- T&T 係主要超市，$59 免運 code FREE59
- 月 budget $500 CAD
- 每款餸最多食 2-3 餐/週

**How to apply：** 做 meal-prep 相關嘢嗰陣，走 API（localhost:8321），唔好手動改 DB。根據實際使用更新設計。


---

## 由 Claude memory 搬入（2026-08-21）— `project_meal_prep_shopping.md`

原本住喺 `~/.claude/projects/-home-nicole/memory/`，每個 session 都載入。
呢啲係 project-specific，應該 cd 入呢個 repo 先 load。

---
name: Meal Prep Shopping Reminders
description: Items Nicole needs to buy next time - kitchen supplies and Amazon orders
type: project
originSessionId: 1d13e80d-dd48-4621-bdc1-440aa4665a71
---
**Costco Business Centre To Buy（湊 $250 免運）：**

日用品：
- [ ] Cascades 抹手紙 12卷 — $17.89
- [ ] Purex 洗衣液 250 loads — $25.69
- [ ] Kirkland 廁紙 30卷 — $27.99

食物：
- [ ] Cavendish 薯餅 2.5kg — $11.19
- [ ] Cavendish 薯條 4.25kg — $18.19
- [ ] Antonio Amato 意粉 9×500g — $15.49
- [ ] Golden Grill 即沖薯蓉 8包 — $11.59
- [ ] SPAM 午餐肉 4罐 — $15.79
- [ ] Green Giant 忌廉粟米 12罐 — $21.49
- [ ] Prego 意粉醬 3×1.2L — $15.79
- [ ] Siwin 和牛餃子 4kg — $43.49 (考慮中)
- [ ] Villa Ravioli 牛肉意雲吞 2kg — $18.99 (考慮中)
- [ ] Villa Ravioli 芝士意雲吞 2kg — $17.99 (考慮中)
- [ ] Sapporo 一番拉麵 24包 — $21.49 (考慮中)

Subtotal: ~$181 (未計考慮中嘅嘢)

**Amazon To Buy：**
- [ ] 隔渣網 200個裝 (disposable sink strainer mesh bags)
- [ ] 紙皮夾/架 (cardboard holder for recycling)
- [x] 圍裙已買 ✅

**其他：**
- [ ] 洗碗布/抹布
- [ ] 洗衣液（Costco 買）

**下次買餸記住：**
- 永遠唔好買成嚿肉（切唔到）
- 只買：絞肉、火鍋肉片、已切片/塊嘅肉
- 西葫蘆 T&T 兩次都冇貨，試 Superstore/Costco


---

## 由 Claude memory 搬入（2026-08-21）— `feedback_meal_prep_workflow.md`

原本每個 session 都載入。呢啲係 project-specific，cd 入呢個 repo 先 load。

---
name: Meal Prep Dev Workflow
description: When working on meal-prep project, always use API endpoints, never manual DB operations. Update API design based on real usage.
type: feedback
originSessionId: 1d13e80d-dd48-4621-bdc1-440aa4665a71
---
做 meal-prep project 嘅嘢嗰陣，一律透過 API 操作，唔好手動改 database。遇到 API 唔支援嘅 workflow 就即時加新 endpoint。根據實際使用更新設計。

**Why:** Nicole 要確保所有操作都係 production-ready 嘅 flow，唔係 dev hack。手動改 DB 唔會暴露 API 設計嘅問題。

**How to apply:** 每次加食譜、改庫存、plan meals 都走 `http://localhost:8000/api`（dev port 8000）。如果 API 做唔到某個操作（e.g. screenshot import），就先加 endpoint 再用。

## Sub-rule: 唔好強迫計算難量化嘅食材

加食譜嗰陣，遇到「用一啲、難計量」嘅 ingredient（wakame、調味料、湯底、油、鹽、辣椒粉等），**唔好強迫 Nicole 入 quantity**。直接 `quantity=null`，用 `note` 寫「適量」/「少少」/「幾粒」。

**Why:** Nicole 講過：「我不需要去強制計算，因為你不知用幾多，每次很難計算。」叫佢入「5g wakame」係假精準，浪費時間。

**How to apply:**
- Recipe ingredient schema 已經 support `quantity: float | None`
- `POST /api/cook-log` 會 auto-skip `quantity is None` 嘅 ingredient（唔扣 stock，唔產生 deficit）
- 同時 mark 呢類食物做 `is_staple=true` + 長 shelf life（e.g. wakame 730 日）→ shopping aggregator 會 skip
- UI 設計層面：recipe ingredient input 唔好 require quantity field
