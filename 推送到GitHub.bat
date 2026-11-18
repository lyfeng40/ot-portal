@echo off
chcp 65001 >nul
title 推送到 GitHub (lyfeng40/ot-portal)
echo ========================================================
echo   精神科 OT 入口網 - 推送到 GitHub
echo   目標倉庫: https://github.com/lyfeng40/ot-portal.git
echo   推送帳號: lyfeng40
echo ========================================================
echo.
cd /d "C:\Users\PC201077\Desktop\AI TRY\精神科OT入口網"
echo [1/2] 檢查本地 Git 狀態...
git status
echo.
echo [2/2] 正在執行 git push origin main ...
git push origin main
echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================================
    echo   [成功] 已順利推送到 GitHub (lyfeng40/ot-portal)！
    echo ========================================================
) else (
    echo ========================================================
    echo   [提示] 若彈出瀏覽器登入視窗，請點選以 lyfeng40 授權登入。
    echo ========================================================
)
echo.
pause
