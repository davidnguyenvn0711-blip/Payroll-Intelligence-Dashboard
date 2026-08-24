#!/bin/zsh
set -e
cd "${0:A:h}/.."
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
.venv/bin/python -m streamlit run streamlit_app.py
