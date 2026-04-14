# Nexus Memory: 專案事實與決策紀錄

## 1. 專案狀態
- **當前階段**: Phase 2 (LangGraph Brain 深化)。
- **已完成架構**: 
    - P0: FastAPI Gateway, Redis Bus, CLI Monitor。
    - P1: PC Agent (CLI Console)。

- 當前開發核心正聚焦於驗證全鏈路測試 (test_nup_flow)。
- 系統目前處於 Phase 2，核心任務為驗證全鏈路測試。
## 2. 關鍵決策
- **記憶系統**: 採用 Markdown 文件驅動 (OpenClaw 風格)，而非傳統資料庫。
- **通訊方式**: 全面使用 Redis Pub/Sub 進行模組間解耦。
