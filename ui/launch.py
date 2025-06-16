# ui/launch.py - Cross-Platform Python Launcher for Regulatory Compliance Analyzer UI

import os
import sys
import subprocess
import time
from pathlib import Path

def print_header():
    """Print the startup header."""
    print("\n🚀 Starting Regulatory Compliance Analyzer UI...")
    print("📍 The UI will be available at: http://localhost:8501")
    print()

def check_directories():
    """Check if we're in the right directory structure."""
    ui_dir = Path(__file__).parent
    project_root = ui_dir.parent
    
    print(f"📂 UI Directory: {ui_dir}")
    print(f"📂 Project Root: {project_root}")
    print()
    
    # Check if we're in the right directory
    if not (ui_dir / "app.py").exists():
        print("❌ Error: app.py not found in UI directory")
        print("Please run this script from the ui/ directory")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Check if main project files exist
    if not (project_root / "compliance_analyzer.py").exists():
        print("❌ Error: Main compliance analyzer not found")
        print("Please ensure you're running from the correct project structure")
        input("Press Enter to exit...")
        sys.exit(1)
    
    return ui_dir, project_root

def check_python():
    """Check if Python is available and get version."""
    try:
        result = subprocess.run([sys.executable, "--version"], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Python found: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError:
        print("❌ Error: Python not found")
        input("Press Enter to exit...")
        sys.exit(1)

def install_requirements(ui_dir):
    """Install UI requirements if needed."""
    requirements_flag = ui_dir / ".requirements_installed"
    requirements_file = ui_dir / "requirements.txt"
    
    if not requirements_flag.exists():
        print("📦 Installing UI requirements...")
        
        if requirements_file.exists():
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)], 
                             check=True)
                requirements_flag.touch()
                print("✅ UI requirements installed successfully")
            except subprocess.CalledProcessError as e:
                print("❌ Failed to install UI requirements")
                print(f"Error: {e}")
                input("Press Enter to exit...")
                sys.exit(1)
        else:
            print("⚠️  No requirements.txt found, skipping installation")
        print()

def check_ollama():
    """Check if Ollama is available and running."""
    print("🔍 Checking Ollama status...")
    
    # Check if Ollama is installed
    try:
        result = subprocess.run(["ollama", "--version"], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Ollama found: {result.stdout.strip()}")
        
        # Check if Ollama is running by trying to list models
        try:
            subprocess.run(["ollama", "list"], 
                         capture_output=True, text=True, check=True, timeout=5)
            print("✅ Ollama is running")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            print("⚠️  Ollama may not be running. Attempting to start...")
            try:
                # Try to start Ollama (this may vary by OS)
                if os.name == 'nt':  # Windows
                    subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                else:  # Unix-like
                    subprocess.Popen(["ollama", "serve"])
                time.sleep(3)
                print("✅ Ollama service started")
            except Exception as e:
                print(f"⚠️  Could not start Ollama automatically: {e}")
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Ollama not found. Please install Ollama first:")
        print("   Visit: https://ollama.ai")
        print()
        print("Press any key to continue anyway, or Ctrl+C to exit")
        try:
            input()
        except KeyboardInterrupt:
            sys.exit(0)

def check_models():
    """Check for available models."""
    print("🤖 Checking available models...")
    
    try:
        result = subprocess.run(["ollama", "list"], 
                              capture_output=True, text=True, check=True)
        llama_models = result.stdout.count("llama3:")
        
        if llama_models == 0:
            print("⚠️  No Llama3 models found. You may need to install a model:")
            print("   ollama pull llama3:8b")
            print("   (continuing anyway...)")
        else:
            print(f"✅ Found {llama_models} Llama3 model(s)")
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Could not check models (continuing anyway...)")

def launch_streamlit(ui_dir):
    """Launch the Streamlit app."""
    print()
    print("🌟 All checks passed! Launching Streamlit app...")
    print()
    print("💡 Tip: To stop the server, press Ctrl+C")
    print()
    
    # Change to the UI directory
    os.chdir(ui_dir)
    
    # Prepare Streamlit command
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", "8501",
        "--server.address", "localhost",
        "--browser.serverAddress", "localhost",
        "--browser.serverPort", "8501",
        "--server.headless", "false",
        "--server.runOnSave", "true",
        "--theme.base", "light",
        "--theme.primaryColor", "#667eea",
        "--theme.backgroundColor", "#ffffff",
        "--theme.secondaryBackgroundColor", "#f0f2f6"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error launching Streamlit: {e}")
    except KeyboardInterrupt:
        print("\n👋 Streamlit app stopped by user")
    
    print("\n👋 Streamlit app has been closed.")

def main():
    """Main launcher function."""
    try:
        print_header()
        ui_dir, project_root = check_directories()
        check_python()
        install_requirements(ui_dir)
        check_ollama()
        check_models()
        launch_streamlit(ui_dir)
        
    except KeyboardInterrupt:
        print("\n👋 Launcher interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()