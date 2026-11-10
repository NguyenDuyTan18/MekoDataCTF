@echo off
REM Khoi dong collector cam flag (phai chay song song voi Docker + round dang running).
REM Giu cua so nay mo suot tran. Dong cua so = flag ngung sinh.
cd /d "%~dp0"
set MEKO_LAB=meko_boutique
echo ============================================================
echo  COLLECTOR FLAG - lab: %MEKO_LAB%
echo  Giu cua so nay MO suot tran dau. Ctrl+C de dung.
echo ============================================================
python collect_checker.py
echo.
echo [Collector da dung] - neu bao "already running" nghia la da co 1 ban khac dang chay.
pause
