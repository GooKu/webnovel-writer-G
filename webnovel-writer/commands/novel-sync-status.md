---
description: 顯示 MD → DB 的同步狀態（哪些檔已修改未 sync、哪些 DB 來源已不存在）
---

# /novel-sync-status

唯讀檢查當前專案的 MD-first 同步狀態。

執行：

```bash
python -X utf8 ".agent/external/webnovel-writer-G/webnovel-writer/scripts/sync_orchestrator.py" \
  --project-root "$(pwd)" status
```

輸出包含：
- **NEW**：尚未 sync 過的 MD
- **CHANGED**：mtime > last_sync 的 MD
- **ORPHAN**：DB 中仍有記錄但 MD 已移除/改名

不寫入 DB，可隨時執行。
