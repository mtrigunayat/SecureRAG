#!/usr/bin/env python
"""
MCP Server Startup Script

Usage:
    python run.py
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    script_dir = Path(__file__).parent
    venv_dir = script_dir / "venv"
    
    print("=" * 60)
    print("MCP Server Startup")
    print("=" * 60)
    
    # Create virtual environment if needed
    if not venv_dir.exists():
        print("Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])
    
    # Determine Python executable in venv
    if sys.platform == "win32":
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:
        python_exe = venv_dir / "bin" / "python"
    
    # Install dependencies
    print("Installing dependencies...")
    subprocess.check_call([str(python_exe), "-m", "pip", "install", "-q", "-r", "requirements.txt"])
    
    # Check environment
    env_file = script_dir / ".env"
    if not env_file.exists():
        print(f"Creating .env from .env.example...")
        example_file = script_dir / ".env.example"
        with open(example_file, "r") as f_in:
            with open(env_file, "w") as f_out:
                f_out.write(f_in.read())
        print("Please edit .env with your configuration")
    
    # Start server
    print("=" * 60)
    print("Starting MCP Server...")
    print("=" * 60)
    
    os.chdir(script_dir)
    subprocess.run([str(python_exe), "-m", "mcp_server.main"])

if __name__ == "__main__":
    main()
