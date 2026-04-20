# 儲存模型規範（Storage Model Specification）

> **版本**：1.0
> **狀態**：webnovel-writer-G fork 正式規範
> **取代**：本規範優先於原 `entity-management-spec.md` 中「SQLite 為主寫入」的描述；原文件已依此規範調整為 MD 優先模型。

---

## 一、核心原則：Single Source of Truth + Derived View

本 fork 採用**MD 主 / DB 衍生**的雙層儲存模型，取代原 webnovel-writer 的「DB 主寫入、MD 可選」設計。

| 層級 | 角色 | 權威性 | 編輯者 | 典型內容 |
|------|------|--------|--------|---------|
| **Markdown（SOT）** | Single Source of Truth | ✅ 權威 | 人類 / AI 協作 | 章節正文、設定文件、流水記錄、伏筆筆記 |
| **SQLite（Derived View）** | 衍生索引與快取 | ❌ 派生 | 同步器自動生成 | 實體索引、流水聚合、章節元資料、座標指標 |

### 三大原則

1. **MD 為真相（MD is Truth）**
   - 所有創作內容與結構化記錄**最終落在 MD**
   - DB 被刪除不構成資料遺失——可從 MD 重建
   - git 追蹤 MD，不追蹤 DB

2. **DB 為派生視圖（DB is Derived View）**
   - DB 的存在目的是**降低 token 消耗**與**加速聚合查詢**
   - DB 內容必須可由 MD 完整重新生成
   - DB 不反寫 MD

3. **可配置同步模式（Configurable Sync Mode）**
   - 由 `novel.config.json` 的 `storage.sync_mode` 決定：`active`（預設）或 `passive`
   - `active`：寫作 / 修改流程末段自動觸發 sync，章節完成即反映到 DB
   - `passive`：僅使用者明確指令（如 `/sync-records`）才觸發；章節可長期處於「已完成、未 sync」狀態
   - 無論哪種模式，**同步方向始終單向**（MD → DB），寫作流程絕不反向讀 DB 後覆寫 MD

---

## 二、儲存分層職責

### 2.1 什麼進 DB

| 資料性質 | 範例 | 儲存位置 | 理由 |
|---------|------|---------|------|
| 數值型變動 | EP +/-、金錢收支、熟練度分數 | `state_changes` 表 | 需 sum / 餘額校驗 |
| 章節元資料 | 章節號、字數、故事內時間戳 | `chapters` 表 | 需排序與聚合 |
| 實體索引 | id / canonical_name / 類型 / tier | `entities` 表 | 查詢入口 |
| 別名對應 | 「墨少年」→「墨飛」 | `aliases` 表 | 消歧查詢 |
| 狀態分類旗標 | 伏筆狀態 `active/resolved/dormant` | 各表的 `status` 欄 | 過濾條件 |
| 關係類型 | 師徒 / 敵對 / 合作 | `relationships` 表 | 圖查詢 |
| **短描述**（≤ 30 字） | 「鍊成失敗反噬」 | 對應表的 `short_reason` 欄 | 摘要性判讀 |
| **MD 指標** | 源 MD 路徑 + 行號錨點 | 各表的 `source_md` / `source_line` 欄 | 定位細節 |

### 2.2 什麼留 MD

| 資料性質 | 範例 | 儲存位置 | 理由 |
|---------|------|---------|------|
| 長段敘述 | 事件完整描寫、人物小傳 | `人物/*.md`、`備註/*.md` | 語境密集、閱讀導向 |
| 伏筆語境 | 真實含義、後續鋪陳邏輯 | `劇情線與伏筆記錄.md` | 劇透敏感、需分層保密 |
| 世界觀細節 | 設定哲學、歷史典故 | `世界觀/*.md` | 文學性內容 |
| 寫作規範 | 用詞、格式、風格要求 | `寫作規範.md` | 人類閱讀頻率高 |
| 章節正文 | `正文/第NNNN章-xxx.md` 或專案自訂 | 由 `novel.config.json` 定義 | 創作產物本體 |

### 2.3 邊界原則

- **凡是需要聚合查詢或餘額校驗的 → DB**
- **凡是需要語境理解或人類閱讀的 → MD**
- **模糊地帶（如伏筆）→ MD 存內容、DB 存索引層**

---

## 三、同步機制

### 3.1 同步方向（強制單向）

```
MD（SOT）─── parser ───→ DB（View）
                 ✗
              （禁止反向）
```

- `sync_md_to_db.py`（或等價工具）是**唯一合法寫入路徑**
- 任何 skill / agent **不得直接 INSERT/UPDATE** DB
- Data Agent 若要新增實體，必須寫入 MD，再觸發同步

### 3.2 觸發時機（依同步模式而異）

#### Active 模式（預設）

寫作 / 修改類 skill 的流程末段**自動觸發** sync：

- `/webnovel-write` 章節寫作完成 → sync
- `/webnovel-review` 若產生修改建議並套用 → sync
- 其他會變動 MD 的 skill 完成時 → sync

**適用情境**：作者願意讓 DB 緊跟 MD 最新狀態、反覆修改頻率不高、偏好「章節完成即一切就緒」的體驗。

#### Passive 模式

僅使用者明確觸發：

- 指令：「sync」、「同步記錄」、「更新流水」
- 專用 skill：`/sync-records`
- Review / 查詢前偵測到 MD mtime > last_sync 時，**提示**使用者是否先同步（不自動執行）

**禁止的自動觸發**（僅 passive 模式）：
- ❌ 寫作 skill 流程末段自動 sync
- ❌ 章節完成後的 hook 自動 sync

**適用情境**：作者習慣章節完成後反覆打磨、在「寫完」與「定稿」之間有較長間距，希望 DB 只反映使用者認可的定稿狀態，避免污染。

#### 共通規則

無論哪種模式：
- 同步方向始終單向（MD → DB）
- 寫入錯誤時不得自動「修正」MD
- last_sync 狀態須持久化，以便跨 session 判斷 MD 是否較新

### 3.3 同步流程

```
1. 掃描 config 定義的所有 MD 來源
2. 解析結構化區塊（表格、frontmatter 欄位）
3. 以 MD 為準，對 DB 執行 upsert
4. DB 中來源已刪除的 record → 標記 tombstone 或刪除（依 config）
5. 寫入 .webnovel/last_sync.json（含 hash / timestamp / 來源 mtime）
6. 輸出同步報告（新增 / 更新 / 刪除計數 + 異常）
```

### 3.4 衝突處理

MD 為 SOT 意味著**不存在雙寫衝突**——DB 永遠配合 MD。唯一可能的「衝突」是：

- **解析失敗**：MD 格式破損（例：流水表欄位缺失）→ sync 中止、保留舊 DB、報錯給使用者
- **引用不存在實體**：MD 記錄變動但實體未定義 → 報 warning、跳過該筆
- **餘額不一致**：MD 餘額欄與 delta 累加結果不符 → 以 MD 標示餘額為準，記 warning

**禁止**：同步器自動「修正」MD。所有異常由使用者決定如何處理。

---

## 四、MD 格式約定

為使 MD 可被可靠解析，需遵守以下格式約定（適用於入 DB 的結構化內容）：

### 4.1 流水型文件（EP / 金錢 / 熟練度）

```markdown
# EP 記錄

## 流水表
<!-- 此區塊由 sync 解析，欄位順序固定 -->
| 章節 | 事件 | 變動 | 餘額 | 來源段落 |
|------|------|------|------|---------|
| 001 | 初始值 | +100 | 100 | - |
| 015 | 鍊成失敗反噬 | -30 | 70 | L42-L48 |

## 備註
（此區塊不解析，人類自由書寫）
```

**要求**：
- 必須存在 `## 流水表` 標題作為解析錨點
- 表頭順序與欄位名稱固定
- 章節欄須為整數，變動欄以 `+`/`-` 開頭
- 「來源段落」格式：`LNNN` 或 `LNNN-LMMM`，`-` 表示無來源（初始值等）

### 4.2 伏筆記錄

```markdown
## FS_001 兜帽人真實身份

- **狀態**：active
- **埋設章節**：023
- **揭曉章節**：（未揭）
- **層級**：作者 only

### 內容
（自由敘述）
```

**要求**：
- 二級標題格式 `## {id} {title}`，`id` 以 `FS_` 起頭
- 前四項 metadata 為 list item，格式固定
- `### 內容` 以下不解析

### 4.3 章節元資料

章節 MD 可選 frontmatter：

```markdown
---
chapter: 15
word_count: 2100
story_time: "第三日 清晨"
scenes: ["鍊金室", "黑市"]
---

# 第十五章 ...
```

Frontmatter 缺失時，同步器依檔名 pattern 推斷章節號，其他欄位從正文掃描。

### 4.4 格式演進

新增欄位須遵守：
1. 不刪除既有欄位（可 deprecate 但保留解析）
2. 新欄位預設值由 parser 填入，舊 MD 無須回填
3. schema migration 由同步器內部處理，不要求使用者批量改 MD

---

## 五、可配置性（novel.config.json 整合）

本儲存模型所有路徑與行為皆由專案 `novel.config.json` 定義：

```jsonc
{
  "storage": {
    "db_dir": ".webnovel",
    "db_file": "index.db",
    "sync_state_file": "last_sync.json",
    "sync_mode": "active",       // "active"（預設）| "passive"
    "gitignore": true
  },
  "features": {
    "structured_storage": true
  },
  "sync_sources": {
    "ep_ledger": {
      "md": "Confirmed/設定/大綱/正篇/備註/EP記錄.md",
      "type": "ledger",
      "entity_id": "protagonist_ep"
    },
    "money_ledger": {
      "md": "Confirmed/設定/大綱/正篇/備註/貨幣流水記錄.md",
      "type": "ledger",
      "entity_id": "protagonist_money"
    },
    "foreshadowings": {
      "md": "Confirmed/設定/大綱/正篇/備註/劇情線與伏筆記錄.md",
      "type": "foreshadowing"
    }
  }
}
```

- `features.structured_storage: false` 時，sync 流程完全停用，所有查詢退回純 MD 讀取
- `storage.sync_mode` 預設 `"active"`；偏好章節反覆打磨者可改為 `"passive"`
- `sync_sources` 是白名單：未列入的 MD 不會被同步器處理
- `storage.gitignore: true` 僅為提示（建議該目錄進 `.gitignore`），同步器**不自動修改** `.gitignore`

---

## 六、Schema 定義

### 6.1 核心表（必備）

```sql
-- 實體表
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    tier TEXT DEFAULT '裝飾',
    short_desc TEXT,              -- ≤ 30 字
    source_md TEXT NOT NULL,      -- MD 指標
    source_anchor TEXT,           -- 錨點（heading / line）
    first_appearance INTEGER,
    last_appearance INTEGER,
    created_at TEXT,
    updated_at TEXT
);

-- 狀態變化表（流水）
CREATE TABLE state_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    field TEXT NOT NULL,
    delta INTEGER,                -- 數值變動（可為 null）
    value_after TEXT,             -- 變動後的值（數值或狀態）
    short_reason TEXT,            -- ≤ 30 字摘要
    source_md TEXT NOT NULL,
    source_line INTEGER,
    chapter_md TEXT,              -- 對應章節 MD
    chapter_line_range TEXT,      -- 章節中的行範圍
    created_at TEXT
);

-- 別名表
CREATE TABLE aliases (
    alias TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    PRIMARY KEY (alias, entity_id, entity_type)
);

-- 伏筆索引表
CREATE TABLE foreshadowings (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,         -- active / resolved / dormant
    visibility_tier TEXT,         -- 對應 CLAUDE.md 資訊視角分層
    planted_chapter INTEGER,
    resolved_chapter INTEGER,
    source_md TEXT NOT NULL,
    source_anchor TEXT
);

-- 章節元資料
CREATE TABLE chapters (
    chapter_num INTEGER PRIMARY KEY,
    title TEXT,
    word_count INTEGER,
    story_time TEXT,
    scenes TEXT,                  -- JSON array
    md_path TEXT NOT NULL,
    synced_at TEXT
);

-- 關係表
CREATE TABLE relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_entity TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    type TEXT NOT NULL,
    short_desc TEXT,              -- ≤ 30 字
    chapter INTEGER,
    source_md TEXT,
    UNIQUE(from_entity, to_entity, type)
);
```

### 6.2 約束

- 所有表的**文字描述欄**（`short_desc` / `short_reason`）**硬上限 30 字**。超過 30 字的敘述一律留 MD，DB 只存摘要
- 所有變動類 record 必須有 `source_md`，確保「從 DB 反查 MD」永遠可行
- 新增表須延續「短描述 + MD 指標」原則

---

## 七、查詢介面

### 7.1 典型查詢

| 用途 | SQL 示例 | token 成本 |
|------|---------|-----------|
| 主角當前 EP | `SELECT value_after FROM state_changes WHERE entity_id='protagonist_ep' ORDER BY chapter DESC LIMIT 1` | < 10 |
| 指定章節的所有變動 | `SELECT * FROM state_changes WHERE chapter = ?` | < 200 |
| 未解伏筆清單 | `SELECT id, title FROM foreshadowings WHERE status='active'` | < 300 |
| 最近 5 章的實體出場 | `SELECT DISTINCT entity_id FROM state_changes WHERE chapter >= ?` | < 100 |

### 7.2 細節讀取流程

Claude 查詢 DB 獲得摘要與 MD 指標後，若需細節：
1. 讀取 `source_md`
2. 依 `source_line` 或 `source_anchor` 跳到精確位置
3. 只讀鄰近段落（通常 ±20 行），不讀整份 MD

此流程確保查詢總 token 成本 = DB 摘要（< 1KB）+ 必要段落（< 1KB），遠低於純 MD 的全文讀取。

---

## 八、重建保證

任何時候，使用者應可執行：

```bash
rm .webnovel/index.db .webnovel/last_sync.json
python .agent/scripts/sync_md_to_db.py --full-rebuild
```

達成的結果**必須與**正常增量同步累積的 DB 狀態**完全一致**（忽略 timestamp 欄位）。

此保證的意義：
- DB 永遠是可拋棄的
- 任何 DB 層的 bug 可藉全量重建修復
- 跨機器協作時，拉取 MD 後在本機重建 DB 即可

---

## 九、與 upstream webnovel-writer 的差異

| 面向 | upstream | 本 fork（webnovel-writer-G） |
|------|----------|----------------------------|
| 權威來源 | DB（index.db） | MD |
| 寫入路徑 | Data Agent → DB | Human/AI → MD → sync → DB |
| 同步時機 | 章節寫作流程末段自動 | 可配置（預設 active 自動，可切 passive 手動） |
| DB 內容 | 完整實體狀態 + 描述 | 索引 + 短描述 + MD 指標 |
| MD 角色 | 可選備註 | 必備 SOT |
| 衝突處理 | DB 為準 | MD 為準，DB 配合 |

---

## 十、遷移策略（對從 upstream 遷入的使用者）

若原專案採 upstream 模式（DB 為 SOT）：

1. **匯出 DB 內容為 MD**：執行 `db_to_md.py`（需另行實作），將現有 DB 轉成符合本規範的 MD 格式
2. **人工審閱 MD**：確認匯出結果符合預期
3. **刪除舊 DB**
4. **啟用 `features.structured_storage`**，從 MD 全量重建 DB
5. **往後維護走 MD-first 流程**

---

## 附錄：為何採用 MD-first

1. **git 友善**：純文字 diff 可讀，不會出現二進位衝突
2. **人類可讀**：作者無需學 SQL 即可檢視與修改
3. **備份內建**：既有 git 歷史即為完整版本控制，無需額外 DB 備份策略
4. **降低耦合**：DB 壞了不影響創作，可隨時重建
5. **對齊本 fork 既有工作流**：novel_work 專案已建立穩定的 MD 備註體系，strongly-typed DB 不該推翻該基礎
