@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem ================= 改这里切换实验 =================
set "MODEL=gpt2-medium"
set "DATA=xsum_gpt2_xl"
rem =================================================

set "PY=G:\anaconda\envs\lastde-repro\python.exe"
set "OUT=results\r_%MODEL%.csv"
set "LOG=results\run_%MODEL%.log"

set "TMP=%~dp0tmp"
set "TEMP=%~dp0tmp"
set "HF_ENDPOINT=https://hf-mirror.com"

if not exist results mkdir results

echo Running model=%MODEL%  data=%DATA% ...
echo.

"%PY%" lastde_repro.py --data %DATA% --model %MODEL% --out "%OUT%" > "%LOG%" 2>&1

type "%LOG%"

echo.
echo ==================================================
echo DONE.  results: %OUT%
echo        log    : %LOG%
echo ==================================================
pause
