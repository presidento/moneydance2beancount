@echo off
IF NOT EXIST .venv\ py -3.7 -m venv .venv --prompt md2bean
call .venv\Scripts\activate.bat
python -m pip -q install -r requirements.txt
