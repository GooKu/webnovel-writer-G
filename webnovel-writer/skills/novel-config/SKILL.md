---
name: novel-config
description: 小說專案的配置層定義。提供 schema、sample 樣板，以及初始化/讀取 novel.config.json 的規範。此 skill 屬於 webnovel-writer-G 的一環，讓框架適配任意專案目錄結構。
---

# novel-config

## 定位

`novel.config.json` 是專案工作區的**單一事實源**，定義：

- 目錄結構（confirmed / draft / translations）
- 篇章配置（chapters_dir、chapter_pattern、outline、notes_dir）
- 設定文件定位（worldview、writing_spec、characters、glossary）
- 寫作量化規範（字數目標、破折號上限、腳本路徑）
- 外部唯讀資源
- Review 層級與功能開關

**所有 webnovel-writer-G 的 skill 與使用端 CLAUDE.md 應讀取此 config 取得路徑，不得再硬寫死路徑。**

此 skill 的目的是讓 webnovel-writer-G 框架能適配任意專案的既有目錄結構，而非強迫專案遷就框架。

---

## 檔案位置

| 檔案 | 位置 | 用途 |
|------|------|------|
| `novel.config.schema.json` | 此 skill 目錄 | JSON Schema，供 IDE 驗證與補全 |
| `novel.config.sample.json` | 此 skill 目錄 | 範例樣板（虛構專案，非任何真實專案內容） |
| `novel.config.json` | **使用端專案根目錄** | 實際生效的配置，每個專案自行維護、不進入 submodule |

---

## 初始化流程

若使用端專案根目錄**尚未**存在 `novel.config.json`：

1. 複製此 skill 目錄下的 `novel.config.sample.json` 到專案根 → 重新命名為 `novel.config.json`
2. 依實際專案目錄結構修改各欄位
3. 不需要的區塊（如 `translation`、`external_readonly`）可整個刪除
4. 更新 `$schema` 欄位指向 submodule 中此 skill 的 schema 路徑

若**已存在**：直接讀取使用，禁止覆寫。

---

## 讀取規範

### 在 skill / CLAUDE.md 中引用路徑時

1. **先讀使用端專案根的 `novel.config.json`**
2. 從對應欄位取得路徑
3. 以該路徑執行後續操作

### 回退機制

若 `novel.config.json` 不存在或欄位缺失：

- 回退到使用端 CLAUDE.md 中原本硬寫死的路徑
- 向使用者警示：「建議執行 novel-config 初始化以集中管理路徑」

---

## 路徑解析慣例

- Config 中所有路徑皆為**相對於使用端專案根目錄**的相對路徑
- 不使用絕對路徑
- 跨平台路徑一律使用正斜線 `/`

---

## Schema 驗證

修改 `novel.config.json` 後可透過 IDE（VSCode）依 `$schema` 欄位自動驗證。

手動驗證（若安裝 `ajv`）：

```bash
npx ajv validate \
  -s .agent/external/webnovel-writer-G/webnovel-writer/skills/novel-config/novel.config.schema.json \
  -d novel.config.json
```

---

## 版本管理

- `version` 欄位採 SemVer `主.次`
- Schema 破壞性變更時升主版號，並在此 SKILL.md 增補遷移說明
- 當前版本：`1.0`
