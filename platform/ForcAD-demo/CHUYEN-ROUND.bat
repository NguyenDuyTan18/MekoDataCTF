@echo off
REM Chuyen ForcAD sang mot lab/round khac QUA HTTP ADMIN API (khong can docker).
REM Dung: CHUYEN-ROUND.bat <ten_lab>     (vd: CHUYEN-ROUND.bat round1)
setlocal
cd /d "%~dp0"
set LAB=%1
if "%LAB%"=="" set /p LAB=Nhap ten lab dich (round1 / meko_boutique):

echo.
echo ============================================================
echo  DRY-RUN: xem ke hoach chuyen sang lab "%LAB%"
echo ============================================================
python switch_round.py --to %LAB%

echo.
echo ------------------------------------------------------------
echo  Neu ke hoach dung, THUC HIEN that bang:
echo    python switch_round.py --to %LAB% --yes --stop --start
echo  ( --stop tu dung round dang chay; --start bat round moi luon )
echo  Sau khi bat: chay BAT-FLAG.bat voi MEKO_LAB=%LAB%.
echo ------------------------------------------------------------
pause
