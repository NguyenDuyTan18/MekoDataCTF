@echo off
python "%~dp0meko.py" %*
if /i not "%~1"=="" if /i not "%~1"=="status" if /i not "%~1"=="config" pause
