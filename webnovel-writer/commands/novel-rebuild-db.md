---
description: 從所有 MD 全量重建 index.db（呼應 MD-first「刪 DB 不損資料」保證）
---

# /novel-rebuild-db

⚠️ **destructive action** — 會刪除現有 `index.db`，從所有 MD 全量重建。執行前請確認。

**使用時機：**
- DB 損壞或 schema 升級
- 懷疑增量 sync 漂移、想重置基準
- 切換 parser 後需重新解析全庫

**安全機制：**
- 自動備份舊 DB 至 `index.db.bak.YYYYMMDD_HHMMSS`
- 重建後同步移除 orphan（disk 已不存在的 source）

執行：

```bash
python -X utf8 ".agent/external/webnovel-writer-G/webnovel-writer/scripts/sync_orchestrator.py" \
  --project-root "$(pwd)" rebuild
```
