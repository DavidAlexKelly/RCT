@echo off
REM ui/launch.bat - Windows Batch Launcher for Regulatory Compliance Analyzer UI

echo.
echo 🚀 Starting Regulatory Compliance Analyzer UI...
echo 📍 The UI will be available at: http://localhost:8501
echo.

REM Get the directory where this script is located
set "UI_DIR=%~dp0"
set "PROJECT_ROOT=%UI_DIR%.."

echo 📂 UI Directory: %UI_DIR%
echo 📂 Project Root: %PROJECT_ROOT%
echo.

REM Check if we're in the right directory
if not exist "%UI_DIR%app.py" (
    echo ❌ Error: app.py not found in %UI_DIR%
    echo Please run this script from the ui\ directory
    pause
    exit /b 1
)

REM Check if main project files exist
if not exist "%PROJECT_ROOT%\compliance_analyzer.py" (
    echo ❌ Error: Main compliance analyzer not found
    echo Please ensure you're running from the correct project structure
    pause
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python not found in PATH
    echo Please install Python and add it to your PATH
    pause
    exit /b 1
)

REM Install UI requirements if needed
if not exist "%UI_DIR%.requirements_installed" (
    echo 📦 Installing UI requirements...
    
    if exist "%UI_DIR%requirements.txt" (
        pip install -r "%UI_DIR%requirements.txt"
        if errorlevel 1 (
            echo ❌ Failed to install UI requirements
            pause
            exit /b 1
        ) else (
            echo. > "%UI_DIR%.requirements_installed"
            echo ✅ UI requirements installed successfully
        )
    ) else (
        echo ⚠️  No requirements.txt found, skipping installation
    )
    echo.
)

REM Check if Ollama is available
echo 🔍 Checking Ollama status...
ollama --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Ollama not found. Please install Ollama first:
    echo    Visit: https://ollama.ai
    echo.
    echo Press any key to continue anyway, or Ctrl+C to exit
    pause >nul
) else (
    echo ✅ Ollama is available
    
    REM Check if Ollama is running by trying to list models
    ollama list >nul 2>&1
    if errorlevel 1 (
        echo ⚠️  Ollama may not be running. Starting Ollama...
        start /b ollama serve
        timeout /t 3 /nobreak >nul
        echo ✅ Ollama service started
    ) else (
        echo ✅ Ollama is running
    )
)

REM Check for required models
echo 🤖 Checking available models...
for /f %%i in ('ollama list 2^>nul ^| find /c "llama3:"') do set MODEL_COUNT=%%i
if "%MODEL_COUNT%"=="0" (
    echo ⚠️  No Llama3 models found. You may need to install a model:
    echo    ollama pull llama3:8b
    echo    ^(continuing anyway...^)
) else (
    echo ✅ Found %MODEL_COUNT% Llama3 model^(s^)
)

echo.
echo 🌟 All checks passed! Launching Streamlit app...
echo.
echo 💡 Tip: To stop the server, press Ctrl+C in this window
echo.

REM Change to the UI directory
cd /d "%UI_DIR%"

REM Launch Streamlit with the app
streamlit run app.py ^
    --server.port 8501 ^
    --server.address localhost ^
    --browser.serverAddress localhost ^
    --browser.serverPort 8501 ^
    --server.headless false ^
    --server.runOnSave true ^
    --theme.base "light" ^
    --theme.primaryColor "#667eea" ^
    --theme.backgroundColor "#ffffff" ^
    --theme.secondaryBackgroundColor "#f0f2f6"

echo.
echo 👋 Streamlit app has been closed.
pause