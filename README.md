 1. 準備工作 (環境檢查)
  確保後端已經重啟以加載最新的代碼變動：

   1 python3 src/gateway/main.py

  2. 測試步驟 (Step-by-Step)

  Step A: 驗證「探索本能 (Discovery)」
  啟動 python3 src/agent/cli_interactive.py 並詢問：
  > 「嘿 Nexus，你現在具備哪些擴充技能？」
   * 預期行為：Nexus 應該產生一個 [THOUGHT] 決定呼叫 discover_skills，並回傳您剛才建立的技能資料夾名稱。

  Step B: 驗證「學習本能 (Reading Spec)」
  接著詢問：
  > 「請幫我看看 [您的技能名稱] 的詳細使用指南是什麼？」
   * 預期行為：Nexus 會呼叫 read_skill_spec(skill_name="您的技能名稱")。
   * 關鍵觀察：它是否能精準摘要出您在 SKILL.md 裡寫的指令和步驟。

  Step C: 驗證「執行本能 (Action)」
  下達一個具體指令來觸發該技能，例如：
  > 「幫我用 [您的技能名稱] 去讀一下 google.com」 (假設是網頁讀取技能)
   * 預期行為：Nexus 應該會組合出正確的 CLI 指令，並呼叫 run_shell。
   * 最終驗證：觀察它是否拿到了 CLI 執行的輸出結果並回覆給您。

  ---

  3. 進階驗證：自主工作測試 (Proactive Test)
  如果您想驗證它是否會在「工作時間」主動使用新技能：
   1. 手動修改 src/brain/vault/identity/soul/schedule.md，將目前的小時設為「工作時間」。
   2. 重啟 gateway/main.py 並觀察日誌輸出。
   * 預期行為：心跳循環會觸發，大腦應該會主動去 discover_skills 並嘗試執行它「想做」的研究任務。

  ---

  故障排除提示：
   * 如果它沒列出技能：檢查 src/skills/ 下是否有子目錄，且子目錄內是否有 SKILL.md。
   * 如果 run_shell 報錯：確保該 CLI 工具（如 playwright）在您的系統路徑中可執行。

  您可以現在開始執行 Step A，並告訴我它是否成功發現了您剛添加的技能？我也能協助您查看日誌來除錯。



幫我去medium看看最近有哪些值得推薦給我的文章



1. 你需要檢查修改過後其他的模塊是否依舊可以兼容
2. 你需要另外撰寫一份文件說明如果今天調整了系統功能需要檢查哪些模塊的相容性
3. 整理目前的文件


