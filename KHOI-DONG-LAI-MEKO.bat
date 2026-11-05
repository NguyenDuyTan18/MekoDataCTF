@echo off
rem Khoi dong lai toan bo he thong cho lab Meko Boutique.
rem Chay file nay tu thu muc goc workspace. Can Docker Desktop dang bat.
setlocal
set "ROOT=%~dp0"
set "FORCAD=%ROOT%platform\ForcAD-demo"
set "MEKO_LAB=meko_boutique"

echo ============================================================
echo   KHOI DONG LAI MEKO BOUTIQUE
echo ============================================================

echo [1/5] Kiem tra Docker...
docker version >nul 2>&1
if errorlevel 1 (
  echo    Docker chua chay. Hay mo Docker Desktop roi chay lai file nay.
  pause
  exit /b 1
)

echo [2/5] Dung va khoi dong lai cac container ForcAD...
pushd "%FORCAD%"
docker compose up -d --build
if errorlevel 1 (
  echo    Loi khi khoi dong container. Xem log o tren.
  popd
  pause
  exit /b 1
)

echo [3/5] Cho database san sang...
set /a tries=0
:waitdb
docker compose exec -T postgres pg_isready -U forcad >nul 2>&1
if not errorlevel 1 goto dbready
set /a tries+=1
if %tries% geq 30 (
  echo    Database chua san sang sau 60 giay. Kiem tra log postgres.
  popd
  pause
  exit /b 1
)
timeout /t 2 >nul
goto waitdb
:dbready

echo [4/5] Cap nhat schema (cot lab, started_at, do dai flag)...
docker compose exec -T ticker python /app/scripts/setup_round1.py
if errorlevel 1 (
  echo    Loi khi cap nhat schema. Xem log o tren.
  popd
  pause
  exit /b 1
)
popd

echo [5/5] Mo collector va trang dieu khien...
start "Meko Collector" cmd /k "cd /d %ROOT% & set MEKO_LAB=meko_boutique & py platform\ForcAD-demo\collect_checker.py || python platform\ForcAD-demo\collect_checker.py"
timeout /t 2 >nul
start "" "http://127.0.0.1:18080/"

echo ============================================================
echo   XONG. Cua so "Meko Collector" phai giu mo suot buoi chay.
echo.
echo   Tren trang dieu khien:
echo    - Neu dang o lab khac: Dung, Dong va luu ho so, roi
echo      bam "Chuan bi Meko Boutique (5 task)".
echo    - Bam "Bat dau" de mo dong ho 50 phut va sinh flag.
echo ============================================================
pause
endlocal
