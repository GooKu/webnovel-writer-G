# 系统架构与模块设计

> ⚠️ **本 fork（webnovel-writer-G）采用 MD-first 储存模型**：Markdown 为 Single Source of Truth，`index.db` 为衍生视图。详见 [`storage-model.md`](storage-model.md)（繁体）。本文件的数据层与 Data Agent 描述已据此调整。

## 核心理念

### 防幻觉三定律

| 定律 | 说明 | 执行方式 |
|------|------|---------|
| **大纲即法律** | 遵循大纲，不擅自发挥 | Context Agent 强制加载章节大纲 |
| **设定即物理** | 遵守设定，不自相矛盾 | Consistency Checker 查询 `index.db` 校验（机器查询以 DB 为主） |
| **发明需识别** | 新实体须登记入 MD，由 sync 派生到 DB | Data Agent 提议写入 MD，使用者确认后被动 sync |

### Strand Weave 节奏系统

| Strand | 含义 | 理想占比 | 说明 |
|--------|------|---------|------|
| **Quest** | 主线剧情 | 60% | 推动核心冲突 |
| **Fire** | 感情线 | 20% | 人物关系发展 |
| **Constellation** | 世界观扩展 | 20% | 背景/势力/设定 |

节奏红线：

- Quest 连续不超过 5 章
- Fire 断档不超过 10 章
- Constellation 断档不超过 15 章

## 总体架构图

```text
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code                           │
├─────────────────────────────────────────────────────────────┤
│  Skills (8个): init / plan / write / review / query /      │
│               sync-records / ...                           │
├─────────────────────────────────────────────────────────────┤
│  Agents (8个): Context / Data / 多维 Checker               │
├─────────────────────────────────────────────────────────────┤
│  SOT Layer:      Markdown（权威）                           │
│  Derived Layer:  state.json / index.db / vectors.db        │
│                   ↑ 由 sync-records 从 MD 派生              │
└─────────────────────────────────────────────────────────────┘
```

## 双 Agent 架构

### Context Agent（读）

职责：在写作前构建"创作任务书"，提供本章上下文、约束和追读力策略。**机器查询以 `index.db` 为主**（效率与 token 考量），仅在需要长叙述/原文时回查 MD。

### Data Agent（提议写入 MD）

职责：从正文提取实体与状态变化，**提议写入对应 MD 文件**（人物档 / 流水 MD / 伏笔档）。Data Agent **不直接写 DB**——MD 定稿后由使用者被动触发 `sync-records` 统一入库。详见 [`storage-model.md`](storage-model.md)。

## 六维并行审查

| Checker | 检查重点 |
|---------|---------|
| High-point Checker | 爽点密度与质量 |
| Consistency Checker | 设定一致性（战力/地点/时间线） |
| Pacing Checker | Strand 比例与断档 |
| OOC Checker | 人物行为是否偏离人设 |
| Continuity Checker | 场景与叙事连贯性 |
| Reader-pull Checker | 钩子强度、期待管理、追读力 |
