# Drohnen Design

Installable application for processing design orders with GUI.

## Installation on Ubuntu

### Run from source
1. Install system dependencies:
   ```bash
   sudo apt install python3 python3-tk python3-venv
   ```
2. Create a virtual environment and install the package:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install .
   ```
3. Launch the application:
   ```bash
   drohnendesign
   ```

### Build a standalone executable
This repository includes a helper script using [PyInstaller](https://pyinstaller.org/) to
create a single-file executable similar to a Windows `.exe`.

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Run the build script:
   ```bash
   ./build_executable.sh
   ```
3. The binary is created in `dist/drohnendesign`. You can copy this file to another Ubuntu
   system and run it directly.

