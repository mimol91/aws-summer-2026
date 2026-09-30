#!/usr/bin/env bash
# Starts the bilingual web UI against the deployed GovEase runtime.
cd "$(dirname "$0")"
python3 -m pip install -q -r requirements.txt
AWS_REGION=us-west-2 streamlit run app.py --server.port 8501
