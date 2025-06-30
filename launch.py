#!/usr/bin/env python3
"""
Regulatory Compliance Analyzer Launcher
Simplified launcher script for the compliance analysis tool.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Launch the Regulatory Compliance Analyzer."""
    
    print("🚀 Starting Regulatory Compliance Analyzer...")
    print("📍 Opening at: http://localhost:8501")
    print()
    
    # Get directories
    project_root = Path(__file__).parent
    ui_dir = project_root / "ui"
    
    # Basic checks
    required_files = [
        ui_dir / "app.py",
        project_root / "utils",
        project_root / "engine.py",
        project_root / "knowledge_base"
    ]
    
    for file_path in required_files:
        if not file_path.exists():
            print(f"❌ Error: {file_path} not found")
            print("Make sure you're running from the project root directory.")
            return 1
    
    print("✅ All required files found")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return 1
    
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Install requirements if needed
    requirements_file = ui_dir / "requirements.txt"
    if requirements_file.exists():
        print("📦 Installing dependencies...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ], check=True, capture_output=True)
            print("✅ Dependencies installed")
        except subprocess.CalledProcessError:
            print("⚠️ Warning: Could not install some dependencies")
    
    # Check Ollama (optional)
    try:
        result = subprocess.run(["ollama", "list"], 
                              capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            model_count = result.stdout.count("llama3")
            if model_count > 0:
                print(f"✅ Ollama ready ({model_count} Llama3 models)")
            else:
                print("⚠️ No Llama3 models found. Install with: ollama pull llama3:8b")
        else:
            print("⚠️ Ollama not responding")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️ Ollama not found. Install from: https://ollama.ai")
    
    print("\n🌟 Launching web interface...")
    print("💡 Press Ctrl+C to stop")
    print()
    
    # Launch Streamlit
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
        print(f"\n❌ Launch failed: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        return 0

if __name__ == "__main__":
    sys.exit(main())