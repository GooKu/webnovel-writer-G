# 实体管理规范 (Entity Management Specification)

> **适用范围**: 所有实体类型（角色/地点/物品/势力/招式）
> **核心目标**: MD 为 SOT，DB 为派生视图；AI 辅助的实体提取、别名管理、版本追踪
>
> ⚠️ **本 fork 规范变更（webnovel-writer-G）**：本文件已从「DB 为主写入」调整为「MD 为 SOT、DB 为衍生视图」模型。整体原则请先阅读 [`docs/storage-model.md`](../../../docs/storage-model.md)（繁体）。本文件描述的是「DB 作为派生层」的 schema 与接口细节。

---

## 当前规范变更（MD-first 模型）

1. **MD 为 SOT**: 所有实体的权威内容（名称、别名、长描述、状态变化原因）最终落在 Markdown 文件
2. **SQLite 派生**: `index.db` 存储**索引 + 短描述（≤30字）+ MD 指针**，便于聚合查询与降低 token 消耗
3. **短描述上限**: DB 中所有文字描述字段（`short_desc` / `short_reason`）硬上限 30 字，长叙述一律留 MD
4. **可配置同步**: DB 由同步器从 MD 生成；触发时机由 `storage.sync_mode` 决定——`active`（预设，写作流程末段自动）或 `passive`（仅使用者明确指令）
5. **state.json 精简**: 仅保留进度、主角状态、节奏追踪（< 5KB）
6. **AI 辅助提取**: Data Agent 从正文提取候选实体并**写入 MD**，由使用者确认后再触发 sync 入库
7. **置信度消歧**: >0.8 自动采纳候选（写入 MD）、0.5-0.8 警告、<0.5 标记待人工确认
8. **重建保证**: 删除 DB 不构成资料遗失——可随时从 MD 全量重建

> **注意**: XML 标签仍可用于手动标注场景（写入 MD），但主流程不再要求。

---

## 一、存储架构

### 1.1 数据分布

| 数据类型 | 存储位置 | 说明 |
|---------|---------|------|
| 实体 (entities) | index.db | SQLite entities 表 |
| 别名 (aliases) | index.db | SQLite aliases 表 (一对多) |
| 状态变化 | index.db | SQLite state_changes 表 |
| 关系 | index.db | SQLite relationships 表 |
| 章节索引 | index.db | SQLite chapters 表 |
| 场景索引 | index.db | SQLite scenes 表 |
| 进度/配置 | state.json | 精简 JSON (< 5KB) |
| 主角状态 | state.json | protagonist_state 快照 |
| 节奏追踪 | state.json | strand_tracker |

### 1.2 index.db Schema

```sql
-- 实体表
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,  -- 角色/地点/物品/势力/招式
    canonical_name TEXT NOT NULL,
    tier TEXT DEFAULT '装饰',  -- 核心/重要/次要/装饰
    desc TEXT,
    current_json TEXT,  -- JSON 格式的当前状态
    first_appearance INTEGER,
    last_appearance INTEGER,
    is_protagonist INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

-- 别名表 (一对多)
CREATE TABLE aliases (
    alias TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    PRIMARY KEY (alias, entity_id, entity_type)
);

-- 状态变化表
CREATE TABLE state_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT,
    chapter INTEGER,
    created_at TEXT
);

-- 关系表
CREATE TABLE relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_entity TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    chapter INTEGER,
    created_at TEXT,
    UNIQUE(from_entity, to_entity, type)
);
```

### 1.3 各类实体特点

| 实体类型 | 别名复杂度 | 属性变化 | 层级关系 |
|---------|-----------|---------|---------|
| 角色    | 高（多种称呼）| 高（境界/位置/关系）| 无 |
| 地点    | 中（简称/全称）| 低（状态变化）| 有（省>市>区）|
| 物品    | 低（别称较少）| 中（升级/转移）| 无 |
| 势力    | 中（简称/别称）| 中（等级/领地）| 有（总部>分部）|
| 招式    | 低（别名少见）| 中（升级）| 无 |

---

## 二、处理流程

### 2.1 Data Agent 辅助提取（MD-first 流程）

```
章节正文
    ↓
Data Agent (AI 语义分析)
    ↓
┌─────────────────────────────────────────────────────────┐
│ 1. 识别出场实体                                          │
│    - 匹配已有实体（通过 MD 中登记的 aliases）             │
│    - 识别新实体，生成 suggested_id                       │
│                                                          │
│ 2. 置信度评估                                            │
│    ├─ > 0.8: 写入对应 MD（人物档 / 备注流水）            │
│    ├─ 0.5-0.8: 写入 MD 并标注 warning                   │
│    └─ < 0.5: 输出提议清单，等待使用者确认后再写 MD        │
│                                                          │
│ 3. 写入 Markdown（SOT）                                 │
│    - 新角色 → 新建或追加 人物/*.md                       │
│    - 属性变化 → 追加对应流水 MD（如 EP记录.md）          │
│    - 新关系 → 追加 劇情線與伏筆記錄.md 或人物档             │
│    - 格式遵循 storage-model.md 第 4 章约定               │
│                                                          │
│ 4. 触发 sync（依 storage.sync_mode）：                  │
│    - active（预设）：写作流程末段自动 sync               │
│    - passive：等待使用者明确触发 sync-records            │
│    ↓                                                     │
│ 5. sync_md_to_db 读取 MD → upsert index.db              │
│    - entities / aliases / state_changes / ...           │
│                                                          │
│ 6. 更新 state.json (精简，仍由 sync 同步)                │
│    - protagonist_state: 主角状态快照                    │
│    - strand_tracker: 节奏追踪                           │
└─────────────────────────────────────────────────────────┘
    ↓
MD 定稿 → DB 反映 MD 状态
```

**关键差异**：Data Agent **不再直接写 DB**。所有写入统一走 MD → sync → DB 的单向管道。详见 [`docs/storage-model.md`](../../../docs/storage-model.md) 第三章「同步机制」。

### 2.2 查询接口

```bash
# 查询实体
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-entity --id "xiaoyan"

# 查询核心实体
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-core-entities

# 通过别名查找
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-by-alias --alias "萧炎"

# 查询状态变化历史
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-state-changes --entity "xiaoyan"

# 查询关系
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index get-relationships --entity "xiaoyan"
```

---

## 三、标签体系 (可选)

> 当前主流程使用 Data Agent 自动提取。以下标签仅用于**手动标注场景**。

### 3.1 新建实体 (`<entity>`)

```xml
<entity type="角色" id="lintian" name="林天" desc="主角，觉醒吞噬金手指" tier="核心">
  <alias>废物</alias>
  <alias>那个少年</alias>
</entity>

<entity type="地点" id="tianyunzong" name="天云宗" desc="东域三大宗门之一" tier="核心">
  <alias>宗门</alias>
</entity>
```

### 3.2 添加别名 (`<entity-alias>`)

```xml
<entity-alias id="lintian" alias="林宗主" context="成为天云宗主后"/>
<entity-alias ref="林天" alias="不灭战神" context="晋升战神称号后"/>
```

### 3.3 更新属性 (`<entity-update>`)

```xml
<entity-update id="lintian">
  <set key="realm" value="筑基期一层" reason="血煞秘境突破"/>
  <set key="location" value="天云宗"/>
</entity-update>
```

**操作类型**:

| 操作 | 语法 | 说明 |
|------|------|------|
| set | `<set key="k" value="v"/>` | 设置属性值 |
| unset | `<unset key="k"/>` | 删除属性 |
| add | `<add key="k" value="v"/>` | 向数组添加元素 |
| remove | `<remove key="k" value="v"/>` | 从数组删除元素 |
| inc | `<inc key="k" delta="1"/>` | 数值递增 |

---

## 四、ID 生成规则

```python
def generate_entity_id(entity_type: str, name: str, existing_ids: set) -> str:
    """
    生成唯一实体 ID

    规则:
    1. 优先使用拼音（去空格、小写）
    2. 冲突时追加数字后缀
    3. 类型前缀: 物品→item_, 势力→faction_, 招式→skill_, 地点→loc_
    """
    prefix_map = {
        "物品": "item_",
        "势力": "faction_",
        "招式": "skill_",
        "地点": "loc_"
        # 角色无前缀
    }

    pinyin = ''.join(lazy_pinyin(name))
    base_id = prefix_map.get(entity_type, '') + pinyin.lower()

    final_id = base_id
    counter = 1
    while final_id in existing_ids:
        final_id = f"{base_id}_{counter}"
        counter += 1

    return final_id
```

---

## 五、错误处理

### 5.1 别名冲突

当前结构允许 **aliases 一对多**：同一别名可以指向多个实体。

当 `ref="别名"` 命中多个实体且无法消歧时，报错：

```
⚠️ 别名歧义: '宗主' 命中 2 个实体，请改用 id 或补充 type 属性

解决方案:
  1. 改用稳定 id：<entity-update id="...">...</entity-update>
  2. 补充 type（仅能消歧跨类型；同类型重名仍需 id）
```

### 5.2 置信度处理

| 置信度范围 | 处理方式 |
|-----------|---------|
| > 0.8 | 自动采用，无需确认 |
| 0.5 - 0.8 | 采用建议值，记录 warning |
| < 0.5 | 标记待人工确认，不自动写入 |

---

## 六、迁移说明

从旧版结构迁移到当前结构：

```bash
# 运行迁移脚本
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" migrate -- --backup

# 验证迁移结果
python "${SCRIPTS_DIR}/webnovel.py" --project-root "$PROJECT_ROOT" index stats
```

迁移后：
- `index.db` 包含所有实体、别名、状态变化、关系
- `state.json` 仅保留进度、主角状态、节奏追踪
- 旧的 `entities_v3`、`alias_index` 字段会被清理

---

## 七、总结

### 7.1 当前结构的核心改进（MD-first）

1. **MD 为 SOT**: 所有权威内容落在 Markdown，git 友善、可人读
2. **SQLite 派生**: `index.db` 仅存索引/短描述/MD 指针，保持轻量
3. **精简 JSON**: state.json 保持 < 5KB
4. **一对多别名**: 同一别名可映射多个实体
5. **AI 辅助提取**: Data Agent 语义分析 → 写入 MD → 使用者确认 → sync 入 DB
6. **可重建**: 删除 DB 不丢失资料，可从 MD 全量重建

### 7.2 数据流（MD-first）

```
章节正文 → Data Agent → MD（SOT）
                         ├─ 人物档 / 流水 MD / 伏笔 MD
                         └─ 使用者确认
                              ↓
                         sync-records（active 自动 / passive 手动）
                              ↓
                         ├─ index.db（实体/别名/关系/状态变化索引）
                         ├─ state.json（进度/主角状态/节奏）
                         └─ vectors.db（场景向量，可选）
                              ↓
                         Context Agent → 下一章上下文
```

详细规范与格式约定请参见 [`docs/storage-model.md`](../../../docs/storage-model.md)。
