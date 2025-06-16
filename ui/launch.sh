#!/bin/bash
# ui/launch.sh - Launch the Regulatory Compliance Analyzer UI

echo "🚀 Starting Regulatory Compliance Analyzer UI..."
echo "📍 The UI will be available at: http://localhost:8501"
echo ""

# Get the directory where this script is located
UI_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$UI_DIR")"

echo "📂 UI Directory: $UI_DIR"
echo "📂 Project Root: $PROJECT_ROOT"
echo ""

# Check if we're in the right directory
if [ ! -f "$UI_DIR/app.py" ]; then
    echo "❌ Error: app.py not found in $UI_DIR"
    echo "Please run this script from the ui/ directory"
    exit 1
fi

# Check if main project files exist
if [ ! -f "$PROJECT_ROOT/compliance_analyzer.py" ]; then
    echo "❌ Error: Main compliance analyzer not found"
    echo "Please ensure you're running from the correct project structure"
    exit 1
fi

# Install UI requirements if needed
if [ ! -f "$UI_DIR/.requirements_installed" ]; then
    echo "📦 Installing UI requirements..."
    
    if [ -f "$UI_DIR/requirements.txt" ]; then
        pip install -r "$UI_DIR/requirements.txt"
        if [ $? -eq 0 ]; then
            touch "$UI_DIR/.requirements_installed"
            echo "✅ UI requirements installed successfully"
        else
            echo "❌ Failed to install UI requirements"
            exit 1
        fi
    else
        echo "⚠️  No requirements.txt found, skipping installation"
    fi
    echo ""
fi

# Check if Ollama is running
echo "🔍 Checking Ollama status..."
if command -v ollama &> /dev/null; then
    if pgrep -x "ollama" > /dev/null; then
        echo "✅ Ollama is running"
    else
        echo "⚠️  Ollama is not running. Starting Ollama..."
        ollama serve &
        sleep 3
        echo "✅ Ollama started"
    fi
else
    echo "❌ Ollama not found. Please install Ollama first:"
    echo "   Visit: https://ollama.ai"
    exit 1
fi

# Check for required models
echo "🤖 Checking available models..."
MODELS=$(ollama list 2>/dev/null | grep -E "llama3:" | wc -l)
if [ "$MODELS" -eq 0 ]; then
    echo "⚠️  No Llama3 models found. You may need to install a model:"
    echo "   ollama pull llama3:8b"
    echo "   (continuing anyway...)"
else
    echo "✅ Found $MODELS Llama3 model(s)"
fi

echo ""
echo "🌟 All checks passed! Launching Streamlit app..."
echo ""

# Change to the UI directory and launch Streamlit
cd "$UI_DIR"

# Launch Streamlit with the app
streamlit run app.py \
    --server.port 8501 \
    --server.address localhost \
    --browser.serverAddress localhost \
    --browser.serverPort 8501 \
    --server.headless false \
    --server.runOnSave true \
    --theme.base "light" \
    --theme.primaryColor "#667eea" \
    --theme.backgroundColor "#ffffff" \
    --theme.secondaryBackgroundColor "#f0f2f6"