If (-not (Test-Path ".venv")) { py -3.8 -m venv .venv --prompt md2bean }
.venv\Scripts\activate.ps1
python -m pip --quiet install --upgrade pip
python -m pip --quiet install -r requirements.txt
