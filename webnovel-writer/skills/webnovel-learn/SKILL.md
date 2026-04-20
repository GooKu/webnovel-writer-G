---
name: webnovel-learn
description: 从当前会话提取成功模式并写入 project_memory.json
allowed-tools: Read Write Bash
---

## 路徑解析約定（novel-config）

使用端路徑（章節、設定、大綱、備註）**優先**透過 `scripts/config_resolver.py` 讀取 `novel.config.json`，缺失時回退到 webnovel-writer-G 預設路徑。完整對照見 [novel-config/PATH_MAPPING.md](../novel-config/PATH_MAPPING.md)。框架內部狀態（`.webnovel/state.json` 等）**不受此規範管理**。

# /webnovel-learn

## Project Root Guard（必须先确认）

- 必须在项目根目录执行（需存在 `.webnovel/state.json`）
- 若当前目录不存在该文件，先询问用户项目路径并 `cd` 进入
- 进入后设置变量：`$PROJECT_ROOT = (Resolve-Path ".").Path`

## 目标
- 提取可复用的写作模式（钩子/节奏/对话/微兑现等）
- 追加到 `.webnovel/project_memory.json`

## 输入
```bash
/webnovel-learn "本章的危机钩设计很有效，悬念拉满"
```

## 输出
```json
{
  "status": "success",
  "learned": {
    "pattern_type": "hook",
    "description": "危机钩设计：悬念拉满",
    "source_chapter": 100,
    "learned_at": "2026-02-02T12:00:00Z"
  }
}
```

## 执行流程
1. 读取 `"$PROJECT_ROOT/.webnovel/state.json"`，获取当前章节号（progress.current_chapter）
2. 读取 `"$PROJECT_ROOT/.webnovel/project_memory.json"`，若不存在则初始化 `{"patterns": []}`
3. 解析用户输入，归类 pattern_type（hook/pacing/dialogue/payoff/emotion）
4. 追加记录并写回文件

## 约束
- 不删除旧记录，仅追加
- 避免完全重复的 description（可去重）
