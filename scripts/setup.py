#!/usr/bin/env python3
"""ContextForge setup - creates virtual environment and installs dependencies."""

import os
import platform
import subprocess
import sys
from pathlib import Path


def get_data_dir():
    """Get the ContextForge data directory."""
    return Path(os.environ.get("CONTEXTFORGE_DATA_DIR", Path.cwd() / ".contextforge"))


def get_venv_dir():
    """Get the virtual environment directory."""
    return get_data_dir() / "venv"


def get_venv_python(venv_dir):
    """Get platform-appropriate venv Python path."""
    if platform.system() == "Windows":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python3"


def create_venv(venv_dir):
    """Create virtual environment."""
    print(f"Creating virtual environment at {venv_dir}...", file=sys.stderr)
    venv_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        [sys.executable, "-m", "venv", str(venv_dir)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print("Virtual environment created.", file=sys.stderr)


def install_dependencies(venv_python):
    """Install required packages."""
    packages = [
        "sentence-transformers>=2.2.0",
        "numpy>=1.24.0",
        "tree-sitter>=0.22.0",
        "tree-sitter-languages>=1.10.0",
    ]
    print(f"Installing dependencies: {', '.join(packages)}", file=sys.stderr)
    subprocess.check_call(
        [str(venv_python), "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.check_call(
        [str(venv_python), "-m", "pip", "install", "--quiet"] + packages,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print("Dependencies installed.", file=sys.stderr)


def main():
    """Run ContextForge setup."""
    venv_dir = get_venv_dir()
    venv_python = get_venv_python(venv_dir)

    # Check Python version
    if sys.version_info < (3, 10):
        print(f"Error: Python 3.10+ required, found {sys.version}", file=sys.stderr)
        sys.exit(1)

    # Create venv if needed
    if not venv_python.exists():
        create_venv(venv_dir)
    else:
        print("Virtual environment already exists.", file=sys.stderr)

    # Install/update dependencies
    install_dependencies(venv_python)

    # Create models directory for HF cache
    models_dir = get_data_dir() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    print("ContextForge setup complete.", file=sys.stderr)


if __name__ == "__main__":
    main()
