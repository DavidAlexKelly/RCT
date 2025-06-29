import os
import sys
import subprocess
import time
from pathlib import Path

def main():
    """Launch the Regulatory Compliance Analyzer."""
    
    print("\n🚀 Starting Regulatory Compliance Analyzer...")
    print("📍 The web interface will open at: http://localhost:8501")
    print()
    
    # Get directories
    project_root = Path(__file__).parent
    ui_dir = project_root / "ui"
    
    # Basic checks
    if not (ui_dir / "app.py").exists():
        print("❌ Error: ui/app.py not found")
        print("Make sure you're running from the project root directory.")
        return 1
    
    if not (project_root / "utils").exists():
        print("❌ Error: utils directory not found")
        return 1
    
    if not (project_root / "engine.py").exists():
        print("❌ Error: engine.py not found")
        return 1
    
    print("✅ All files found")
    
    # Check Python
    try:
        result = subprocess.run([sys.executable, "--version"], 
                              capture_output=True, text=True, check=True)
        print(f"✅ {result.stdout.strip()}")
    except subprocess.CalledProcessError:
        print("❌ Python not found")
        return 1
    
    # Install UI requirements if needed
    requirements_file = ui_dir / "requirements.txt"
    if requirements_file.exists():
        print("📦 Checking UI requirements...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)], 
                         check=True, capture_output=True)
            print("✅ Requirements satisfied")
        except subprocess.CalledProcessError:
            print("⚠️ Warning: Could not install requirements")
    
    # Check Ollama
    print("🔍 Checking Ollama...")
    try:
        subprocess.run(["ollama", "--version"], 
                      capture_output=True, text=True, check=True)
        print("✅ Ollama found")
        
        # Try to list models
        result = subprocess.run(["ollama", "list"], 
                              capture_output=True, text=True, check=True, timeout=5)
        model_count = result.stdout.count("llama3:")
        if model_count > 0:
            print(f"✅ Found {model_count} Llama3 model(s)")
        else:
            print("⚠️ No Llama3 models found. Install with: ollama pull llama3:8b")
            
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ Ollama not found or not running")
        print("   Install from: https://ollama.ai")
        print("   Continuing anyway...")
    
    print("\n🌟 Launching web interface...")
    print("💡 Tip: Press Ctrl+C to stop the server")
    print()
    
    # Change to UI directory and launch streamlit
    os.chdir(ui_dir)
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--server.headless", "false",
            "--theme.base", "light",
            "--theme.primaryColor", "#667eea"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error launching interface: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n👋 Interface stopped")
        return 0

if __name__ == "__main__":
    sys.exit(main())