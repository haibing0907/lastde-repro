@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY=G:\anaconda\envs\lastde-repro\python.exe"
set "TMP=%~dp0tmp"
set "TEMP=%~dp0tmp"
set "HF_ENDPOINT=https://hf-mirror.com"

if not exist results mkdir results

for %%L in (64 128 256) do (
    echo ==================================================
    echo  Running max-tokens = %%L
    echo ==================================================
    "%PY%" lastde_repro.py --data xsum_gpt2_xl --model gpt2 --max-tokens %%L --out "results\r_len%%L.csv" > "results\run_len%%L.log" 2>&1
    type "results\run_len%%L.log"
    echo.
)

echo ==================================================
echo DONE.  results\r_len64.csv  r_len128.csv  r_len256.csv
echo ==================================================
pause
