# Path Mapping：webnovel-writer-G ↔ novel.config.json

所有使用端路徑均透過 `scripts/config_resolver.py` 取得。框架內部狀態（`.webnovel/`）維持固定，不納入 config 管理。

---

## 路徑對照表

### 使用端路徑（由 novel.config.json 管理）

| 原硬寫死路徑 | config 欄位 | 說明 |
|---|---|---|
| `正文/` | `arcs[current_arc].chapters_dir` | 章節檔所在目錄 |
| `正文/第{NNNN}章-{title}.md` | `arcs[current_arc].chapter_pattern` | 章節檔名模式 |
| `大纲/总纲.md` | `arcs[current_arc].outline` | 卷大綱 |
| `大纲/{章节}.md` | `arcs[current_arc].notes_dir` | 備註目錄 |
| `设定集/世界观.md` | `settings.worldview` | 世界觀總覽 |
| `设定集/人物/` | `settings.characters_dir` | 人物設定目錄 |
| `设定集/词条/` | `settings.glossary_dir` | 詞條目錄 |
| — | `settings.writing_spec` | 絕對寫作規範檔 |
| — | `settings.high_risk_glossary` | 高風險詞條強制讀取清單 |
| — | `paths.confirmed_root` / `paths.draft_root` | 已確認內容與草稿根目錄 |
| — | `translation.output_dir` / `languages` / `glossary` | 翻譯相關 |
| — | `writing.target_words_per_chapter` | 字數目標 |
| — | `writing.dash_limit_per_chapter` | 破折號上限 |
| — | `writing.word_count_script` / `format_audit_script` | 使用端自備腳本 |
| — | `external_readonly.*` | 使用端外部唯讀資源 |

### 框架內部路徑（不納入 config）

| 路徑 | 用途 |
|---|---|
| `.webnovel/state.json` | 進度快照、主角狀態、strand tracker |
| `.webnovel/summaries/ch{NNNN}.md` | 章節摘要 |
| `.webnovel/index.db` | 實體/關係/章節結構化索引 |
| `.webnovel/vectors.db` | 向量嵌入（RAG） |
| `.webnovel/project_memory.json` | `/webnovel-learn` 寫入的可複用模式 |

---

## 呼叫方式

### Python

```python
from config_resolver import resolve_path, resolve_arc_path, format_chapter_filename

chapters_dir = resolve_arc_path(project_root, None, "chapters_dir", default="正文")
pattern = resolve_arc_path(project_root, None, "chapter_pattern", default="第{NNN}章-{title}.md")
filename = format_chapter_filename(pattern, num=45, title="章节标题")

worldview = resolve_path(project_root, "settings.worldview", default="设定集/世界观.md")
```

### Bash（skill 內）

```bash
CHAPTERS_DIR=$(python "${SCRIPTS_DIR}/config_resolver.py" "${PROJECT_ROOT}" \
  get arcs.${CURRENT_ARC}.chapters_dir --default "正文")

WORLDVIEW=$(python "${SCRIPTS_DIR}/config_resolver.py" "${PROJECT_ROOT}" \
  get settings.worldview --default "设定集/世界观.md")
```

### 檢查 config 是否存在

```bash
HAS_CFG=$(python "${SCRIPTS_DIR}/config_resolver.py" "${PROJECT_ROOT}" has-config)
if [ "$HAS_CFG" = "1" ]; then
  echo "使用 novel.config.json"
else
  echo "回退到 webnovel-writer-G 預設路徑"
fi
```

---

## 回退原則

1. `novel.config.json` 不存在 → 使用各 CLI/API 呼叫提供的 `default` 值（即 webnovel-writer-G 原預設路徑）
2. 欄位缺失或為空字串 → 同上
3. 型別錯誤（如預期 string 拿到 object）→ 同上，並由 resolver 靜默忽略
4. 任何回退都**不應阻斷主流程**

---

## 受影響的核心檔案

| 檔案 | 對齊程度 |
|---|---|
| `scripts/config_resolver.py` | 新增 |
| `scripts/chapter_paths.py` | 已 patch：`find_chapter_file` / `default_chapter_draft_path` 改讀 config |
| `scripts/project_locator.py` | 不動（處理 `.webnovel/` 內部狀態） |
| `skills/*/SKILL.md` | 頂部加 banner：路徑透過 resolver 取得 |
| `agents/*.md` | 不動（只做檢查邏輯，不觸及使用端路徑） |
| `templates/` | 不動（例示性文件） |

---

## 限制

- `chapter_pattern` 目前僅支援 `{NNN}` 與 `{title}` 兩個變數
- 新增模式變數需同步修改 `config_resolver.format_chapter_filename` 與 schema
- Resolver 僅做**唯讀**路徑解析，不寫入 config
