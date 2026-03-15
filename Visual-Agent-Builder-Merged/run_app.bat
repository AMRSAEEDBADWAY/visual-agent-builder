@echo off
cd /d "%~dp0"
echo ==========================================
echo   Visual Agent Builder - Windows Launcher
echo ==========================================
echo [INFO] Project Root: %CD%
echo.
REM تحقق مما إذا كانت البيئة الافتراضية موجودة بالفعل
if exist venv_win (
    echo [INFO] Virtual environment found. Skipping setup...
) else (
    echo [INFO] Creating virtual environment...
    python -m venv venv_win
    echo [INFO] Activating virtual environment...
    call venv_win\Scripts\activate.bat
    echo [INFO] Installing requirements...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

REM تفعيل البيئة (في حالة كانت موجودة بالفعل وتخطى السكريبت الجزء العلوي)
if exist venv_win\Scripts\activate.bat (
    call venv_win\Scripts\activate.bat
)
echo.
echo [INFO] Starting Visual Agent Builder...
echo [INFO] Open your browser at: http://localhost:8501
echo.
streamlit run app.py
pause
exit /b 0
