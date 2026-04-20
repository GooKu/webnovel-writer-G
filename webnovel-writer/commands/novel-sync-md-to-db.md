---
description: 將 MD 變動增量同步到 index.db（MD-first 模型的寫入路徑）
---

# /novel-sync-md-to-db

依 `novel.config.json -> storage.scan_paths` 掃描 MD，呼叫 `storage.parser`（未設則用 reference_parser），增量 upsert `index.db`。

**建議流程：**
1. 先執行 `/novel-sync-status` 預覽變動範圍
2. 確認無誤後執行本 command

執行：

```bash
python -X utf8 ".agent/external/webnovel-writer-G/webnovel-writer/scripts/sync_orchestrator.py" \
  --project-root "$(pwd)" sync
```

僅處理 mtime > last_sync 的檔案；對每個檔先 `purge_source` 再重新解析寫入，避免重複。

**何時觸發：**
- `sync_mode: active`：寫作流程末段自動執行（由 skill 內部呼叫）
- `sync_mode: passive`：使用者手動執行本 command
