# 狼人殺練習器：交接文件（給接手的 AI agent）

> 這份文件讓下一個 agent **不需要看先前的對話**就能接手。先讀完「1～5」，動手前再看「6」的檢查清單。
> 最後更新：2026-11-04。

---

## 1. 專案是什麼、為誰做

- **使用者**：jackhsieh806（GitHub），用**繁體中文**溝通，主要用**手機**操作與遊玩。
- **目的**：準備真人狼人殺。他會拿到實際比賽的板子海報（圖片），請 agent 把角色和規則加進練習器，再用電腦對戰、測驗和推理練習。
- **兩個版本，規則和電腦策略完全相同**：
  - **Python CLI**：`python3 -m werewolf`（在 repo 根目錄執行）
  - **手機網頁版**：單一 HTML 檔，所有邏輯都是 JS 移植。
    - 給朋友玩（GitHub Pages，不需帳號）：https://jackhsieh806.github.io/jackh_code/werewolf/play/
    - 使用者自己用（Claude Artifact，私人連結）：https://claude.ai/artifact/MDAJ8Puw8QthvYk4YFn3Fn
- repo 裡的 `werewolf/index.html`、`manifest.json`、`icon.png` 是**另一個 session 做的「推理筆記本」**（iPad 筆記工具），**不是這個練習器，不要動它**。

## 2. 快速開始

```bash
python3 -m werewolf                                # 互動選單：對局 / 觀戰 / 測驗 / 速查 / 設定
python3 -m unittest werewolf.tests.test_engine     # 96 個測試，約 8 秒
python3 werewolf/web/sync_quiz.py                  # 把題庫與電腦個性同步到網頁版
python3 werewolf/web/build_pages.py                # 產生 GitHub Pages 用的 werewolf/play/index.html
python3 werewolf/experiments/harness.py 9 600      # 好人策略實驗（見第 9 節）
```

純 Python 3.10+、無第三方套件。網頁版不需建置工具，驗證時用 node 和 playwright（見第 7 節）。

## 3. 檔案地圖

| 檔案 | 內容 |
|---|---|
| `werewolf/roles.py` | `Role` / `Team` 列舉、`WOLVES`、`GODS`、角色說明 `ROLE_DESCRIPTIONS`、板子 `PRESETS`（key "1"～"9"） |
| `werewolf/engine.py` | **規則引擎**（不含 I/O）：`Rules`、`Speech`、`Player`、`Controller` 介面、`Game`（夜晚、天亮、警長競選、白天、投票、死亡連鎖、勝負判定） |
| `werewolf/bots.py` | `BotController`：電腦推理與決策（約 1000 行，核心在 `analyze` / `suspicion`） |
| `werewolf/personality.py` | 六種電腦個性的參數（5 種隨機池 + 推理高手） |
| `werewolf/human.py` | `HumanController`：真人在 CLI 的輸入 |
| `werewolf/cli.py` | 主選單、選板子、自訂板子、規則設定、復盤 `review()` |
| `werewolf/guide.py` | 速查 `CHEATSHEET`、測驗題（6 個主題共 163 題）、`run_quiz()` |
| `werewolf/tests/test_engine.py` | 96 個 unittest；`Scripted` 可以覆寫個別決策，用來寫確定性的情境測試 |
| `werewolf/web/index.html` | **網頁版原始檔**（也是 Claude Artifact 原始檔），**沒有** doctype、`<head>` 和 viewport |
| `werewolf/web/sync_quiz.py` | 從 `guide.py`、`personality.py` 產生網頁版的 `QUIZ_TOPICS` 與 `PERSONALITIES` 區塊 |
| `werewolf/web/build_pages.py` | 把 `web/index.html` 包成完整 HTML，輸出到 `werewolf/play/index.html`（GitHub Pages 用） |
| `werewolf/play/index.html` | **自動產生，不要手改** |
| `werewolf/experiments/` | 好人策略實驗（見第 9 節） |
| `werewolf/README.md` | 給人看的功能說明與規則清單 |

## 4. 架構重點（一定要知道）

1. **Python 是唯一的事實來源，網頁版是手動移植的 JS 鏡像**。
   - 任何規則或電腦策略的改動，都要在 `engine.py` / `bots.py` 和 `web/index.html` 的 JS 各改一次。
   - 測驗題和電腦個性例外：改 Python 後執行 `sync_quiz.py` 自動同步，**不要手改 JS 裡的這兩個區塊**。
2. **JS 和 Python 的命名對照**：角色 key 有幾個不同（Python → JS）。
   - `AWAKENED_WOLF_KING` → `AWAKENED`、`TIGER_GRANDMA` → `TIGER`、`LANTERN_SEER` → `LANTERN`，其他相同。
   - Python 用 snake_case、JS 用 camelCase（例：`claim_race` → `claimRace`、`knight_gold` → `knightGold`）。
   - JS 引擎全部是 `async`，因為真人要用按鈕回應。JS 用 `Math.random()`（沒有種子）；Python 用 `game.rng`，可以重現。
3. **Controller 介面**：引擎只問 controller「要做什麼」，再驗證合不合法。
   - 不合法的回應一律當成「不行動」，所以電腦或真人亂回也不會壞掉。
   - 新增技能時，要在 `Controller`（Python 預設不行動）、`BotController`、`HumanController` 和 JS 的 `Bot` / `Human` 各加一個方法。
4. **電腦只能用自己身份該知道的資訊**：好人看公開發言、票型、翻牌，加上自己的私人資訊；狼知道隊友。
   - `game.wolf_plan` 是狼隊共用的戰術，只有狼可以讀。
   - 唯一的例外是 `game.last_dream` / `last_guard` 這類「自己的行動紀錄」。
5. **陣營判斷**用 `game.alignment(p)`，不要用 `p.role.team`，因為野孩子的陣營會變。
   - `p.is_wolf` 的意思是「以狼身份行動」，包含轉狼的野孩子。
   - 查驗結果用 `game.check_result()`：野孩子永遠驗出金水。
6. **Artifact 原始檔不能有 doctype**（Claude 平台會自動包外層）。所以 GitHub Pages 用的是 `build_pages.py` 產生的完整版本。

## 5. 目前狀態

- PR #1～#8 都已合併進 `main`；GitHub Pages 由 `.github/workflows/pages.yml` 在 push 到 `main` 時自動部署整個 repo，約 20 秒完成。`gh-pages` 分支是舊的、沒有在用。
- 開發分支：`claude/werewolf-game-logic-n4hvae`。PR 合併後，下一次修改要從最新的 `main` 重開這個分支（`git checkout -B <分支> origin/main`）。
- **使用者的部署習慣**：agent 開 PR → 使用者說「幫我合併讓朋友可以玩」→ agent 合併 → 確認線上網址已經更新。合併前要先得到使用者同意。

### 已實作的板子（`roles.PRESETS`）

| key | 板子 | 好人勝率（全電腦，預設設定） |
|---|---|---|
| 1 | 9 人：3 狼 + 預女獵 + 3 民 | 53% |
| 2 | 12 人 預女獵白 | 50% |
| 3 | 12 人 預女獵守 | 58% |
| 4 | 12 人 狼王守衛 | 57% |
| 5 | 12 人 攝夢人 | 56% |
| 6 | 12 人 奇蹟商人 | **45%** |
| 7 | 12 人 覺醒狼王 | 53% |
| 8 | 15 人 村姑與虎姑婆 | 53% |
| 9 | 15 人 燈影預言家（使用者實戰會玩的板子） | **24%** |

另外有「自訂板子」：自己設定每個角色幾張，可以照實戰配置練習。

### 角色（18 種）
狼人、狼王、覺醒狼王、狼美人、虎姑婆、野孩子、預言家、燈影預言家、女巫、獵人、守衛、白痴、攝夢人、奇蹟商人、騎士、村姑、平民（加上幸運兒道具與親傳狼王爪等衍生狀態）。

### 規則開關（`engine.Rules`）
`witch_self_save`（never / first_night / always）、`same_guard_save_dies`、`win_mode`（side 屠邊 / all 屠城）、`first_night_last_words`、`sheriff`、`self_explode`、`lantern_claim_race`、`bot_personality`、`show_personality`、`smart_bots`（推理高手人數 0～4）、`max_rounds`。

## 6. 修改的標準流程（檢查清單）

1. 改 Python（`engine.py` / `bots.py` / `roles.py` / `human.py` / `cli.py`）。
2. 在 `tests/test_engine.py` 加測試，並確認全部通過。
   - 舊測試的 `quiet_game()` 預設關閉警長、自爆和推理高手，讓結果固定。新功能如果影響預設流程，記得在測試裡明確設定 `Rules(...)`。
3. 跑電腦對戰模擬，確認所有板子都能正常結束、勝率沒有異常（見第 7 節的腳本）。
4. 用隨機輸入測 CLI（fuzz，見第 7 節）。
5. 在 `web/index.html` 移植同樣的改動。
6. 執行 `python3 werewolf/web/sync_quiz.py` 和 `python3 werewolf/web/build_pages.py`。
7. 驗證網頁版：用 node 跑引擎模擬（一半對局加入隨機點按鈕的假真人），再用 playwright 以 iPhone 13 尺寸開 `werewolf/play/index.html`，確認沒有 console error、沒有橫向捲動。
8. 更新 `README.md`、速查（`guide.py` 和 JS 的速查區塊）、測驗題（`guide.py`，再同步）。
9. commit（訊息用英文，結尾附 attribution）、push、更新 Artifact、開 PR 或更新 PR 說明。

## 7. 驗證方法（可以直接複製）

**全電腦模擬（Python）**
```python
import random
from werewolf.engine import Game, deal, Rules
from werewolf.roles import PRESETS, Team
for key, (desc, roles) in PRESETS.items():
    good = sum(Game(deal(roles, random.Random(i)), seed=i, out=lambda _: None, rules=Rules()).play() is Team.GOOD
               for i in range(300))
    print(key, desc[:20], good / 300)
```

**CLI fuzz**：用 `builtins.input = fake` 依序餵入選單選項，之後隨機回答；`contextlib.redirect_stdout` 收集輸出，最後檢查輸出含「遊戲結束」或「平手」。

**網頁引擎模擬（node）**：
1. 把 `index.html` 裡 `<script>` 的內容切到 `// ===... 畫面` 這行之前，就是純引擎。
2. 接上一個 `io` stub（`say / secret / phase / update / pause` 都是空函式）。
3. 用假的 UI 物件建立 `new Human(fakeUI)`，讓 `pickSeat` / `choose` / `compose` 隨機回應。
4. 跑完確認每局都正常結束。

**手機畫面（playwright）**：sandbox 內已有 chromium（`PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`）；在 scratchpad 用 `npm i playwright@1.56.1` 安裝，然後用 `devices['iPhone 13']` 開 `file:///…/werewolf/play/index.html`。

## 8. 規則：海報沒寫清楚、由 agent 決定的地方

接手時**不要悄悄改掉**這些決定；使用者如果提出不同規則，再照他的說法改。

- **同守同救**會死（可在設定裡切換）；**女巫自救**預設僅首夜。
- **狼王／覺醒狼王**：被毒、夢遊出局不能發動；被獵人帶走、自爆可以發動；被帶走的獵人或狼王可以接著發動（連鎖）。
- **奇蹟商人**的「守護」道具是一次性的。
- **警上自爆**：警徽流失（有些地方改成隔天再競選）。自爆沒有遺言；白天自爆後直接天黑。
- **狼美人**：不能自爆、不能被狼隊自刀；被騎士決鬥出局時技能被封（燈影海報有寫，套用到所有板子）。
- **虎姑婆**：被反傷的人仍然會拿到查驗結果；反傷彈到女巫時，虎姑婆不會被毒死。
- **野孩子**：榜樣是虎姑婆時直接加入狼隊；還沒轉狼時，被騎士決鬥算好人（騎士出局）。
- **村姑**：沒有警長票時，看最近一次放逐投票。
- **騎士**：只能在白天輪到自己發言時決鬥，警上不能。
- **被迷魅一同出局**的人沒有遺言。
- **燈影預言家板**：海報配置加起來是 16 人，但標題是 15 人，獲勝條件寫「四民 + 燈影預」，所以用 **4 個平民**。
  - 兩位預言家不能驗自己、翻牌騎士和騎金（騎士決鬥失敗而證實是好人的人）。
  - 燈影預言家算在平民那一邊；預言家算神職。
  - 「四人核心搶警」預設開啟：預言家和燈影預言家兩位真身，加上兩隻狼各悍跳一張牌，四人保證上警；其他玩家也可以參選，候選總數不設上限。這個模式下狼不會警上自爆。

## 9. 進行中的工作：好人策略實驗（被使用者中途打斷）

使用者最後的請求：「能否幫我模擬好人要如何玩才能讓勝率大於 50%」。

`werewolf/experiments/harness.py` 裡的 `GoodBot` 只讓好人陣營換打法，狼人維持原本的策略。可以開關的打法：
- `duel`：騎士決鬥他最不相信的跳預言家者。
- `poison`：女巫第二晚起毒最不相信的跳預言家者。
- `guard`：守衛輪流守他認為的真預言家。
- `focus`：好人懷疑度 +25，集中推對跳的人。

### 舊版燈影預言家板（key 9、四位候選名單固定）的結果，每種打法跑 600 局

> 以下數據是在舊版只有四位固定候選、其他玩家不上警且騎士未保證第三天決鬥的規則下取得。新版允許其他玩家參選，且騎士策略已調整；這些勝率不能直接當作新版結果。

| 打法 | 好人勝率 |
|---|---|
| 基準（目前的打法） | 23% |
| 推理高手 0 位 / 4 位 | 21% / 25% |
| 好人全員邏輯型 | 24% |
| **騎士第 1 天決鬥對跳的人** | **64%** |
| 騎士決鬥 + 守衛守真預言家 | **66%**（目前最佳） |
| 騎士決鬥 + 集中票推 | 62% |
| 騎士第 2 天才決鬥 | 35%（時機很關鍵） |
| 女巫毒對跳的人 | 20%（有害：常毒到真預言家） |
| 守衛守真預言家（單獨） | 28% |
| 集中票推對跳（單獨） | 22% |
| 「各報各的牌」模式：基準 → 加騎士決鬥 | 39% → 51% |

**原因分析**（`lantern_duel_breakdown.py`，800 局）：決鬥的價值在於**資訊**，不只是殺狼。

| 決鬥結果 | 佔比 | 好人勝率 | 第 3 天好人找對真預言家組合 |
|---|---|---|---|
| 成功（決鬥到狼） | 47% | 70% | 86% |
| 失敗（決鬥到真預言家） | 52% | 64% | 75% |
| 沒有決鬥 | 1% | 29% | 57% |

決鬥失敗時，被決鬥的人會變成騎金（證實是好人），那張牌的另一位就一定是狼，所以四人搶警的混亂一樣會被拆掉一半。

### 還沒完成的部分
1. **奇蹟商人板（key 6，45%，沒有騎士）**：`merchant_board.py` 已經寫好，但還沒跑完就被使用者中斷。
   - 要測的打法：推理高手 4 位、全員邏輯型、女巫毒、集中票推、商人首夜必給查驗、商人把守護交給相信的預言家。
   - 下一步：跑完它（`python3 werewolf/experiments/merchant_board.py`），找出能讓勝率超過 50% 的打法。
2. 舊版模擬的真人打法建議（例如第一天決鬥對跳預言家）不能直接套用新版搶警規則；需先以新版規則重新模擬，再整理實戰建議。
3. 新版 `bots.py` 騎士若仍存活且未用技能，第三天會依當時最高懷疑度決鬥；其勝率需依新版搶警規則重新模擬後才能評估。

## 10. 電腦推理設計摘要（`bots.py`）

- **`analyze()`** 整理確定資訊，回傳 `Knowledge`：`good` / `wolf`（確定的）、`trusted`（站邊的預言家）、`claims`；燈影板另有 `evidence` / `protected` / `card_acc`；還有 `sheriff_doubt` / `sheriff_why`、`hints` / `hint_why`（來自推理高手）。
  - 找矛盾：查驗對象是確定好人卻說是狼，查驗者就是狼；反覆推導，直到沒有新結論。
  - **燈影板 `_lantern_analyze()`**：列舉「每張牌選一人當真預言家、再看哪位準」的所有假設，排除條件如下：
    - 兩人驗同一個人結果相同；
    - 兩人互驗結果相同；
    - 查驗和確定身份或隱含身份（對跳者都是狼）矛盾；
    - 查驗時準時反（一定是狼）。
    剩下的假設依直覺加上「晚上被刀的跳預言家比較可能是真的」來評分。
  - **`_sheriff_doubt()`**：獨立評估警長是不是假的，看這些證據：對跳、查驗矛盾、點名或投票給確定好人、狼隊幫他上警長、警徽來自狼、跳預言家多晚都沒被刀。懷疑度 ≥ 0.5 就不再站警長的邊。
  - **`_absorb_findings()`**：參考推理高手公開的漏洞；能用公開資訊驗證的直接採信，其他的依信任程度加權。
- **`suspicion()`** 算出每個人的懷疑度，同時把理由記在 `self.reasons`，發言時用 `explain()` 說出前兩個理由。
- **個性**（`personality.py`）控制這些權重和門檻：直覺 `intuition`、跟風 `follow`、證據 `evidence`、棄票與點名門檻、用毒／開槍／決鬥的門檻、狼的悍跳（`bluff`）與自爆（`explode`）傾向、撕警徽門檻。
  - 推理高手（`detective=True`、`random_pool=False`）只透過 `Rules.smart_bots` 指派給好人，會公開 `find_loopholes()` 找到的漏洞。
- **狼隊**：開局由 `wolf_plan["fake_seers"]` 決定悍跳人選（四人核心搶警指定兩隻狼分別悍跳預言家與燈影預言家），投票統一。夜晚優先刀這些人：真預言家 → 公開找漏洞的推理高手 → 跳女巫的人 → 金水。

## 11. 已知限制與想法

- 電腦的「思考」是評分規則，不是語言模型；發言是模板句，只包含身份、查驗、歸票和理由，讀不出語氣。
- 部分板子的勝率不在 50% 附近（燈影 24%、奇蹟商人 45%），見第 9 節。
- 還沒實作：白狼王、丘比特、黑市商人、警長 PK 時的重新發言、退水。
- 網頁版只有 `localStorage` 記住設定，沒有對戰紀錄保存。
- 想法：在復盤加上「這局警長是誰、拿警徽的陣營勝率」；做「好人策略」設定開關（第 9 節）；讓使用者能在對局中查看某個電腦的完整推理。

## 12. 和使用者溝通的習慣

- 回覆用**繁體中文**，結論先講；有數據就附上模擬數據（局數、勝率）。
- 海報規則有模糊的地方，就自己選一個合理的版本**先做**，最後列出「我自行決定的地方」，讓使用者確認。
- 使用者常用手機看，所以網頁版要先確認手機畫面正常。
- 真人局相關的回答，最後附上可以照做的實戰建議。
