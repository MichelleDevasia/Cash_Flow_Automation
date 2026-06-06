@echo off
REM Activity Tracker Startup Script
echo Starting Activity Tracker Streamlit App...
cd /d "%~dp0"
streamlit run streamlit_app.py
pause
