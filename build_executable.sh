#!/usr/bin/env bash
set -euo pipefail

pyinstaller --name drohnendesign \
  --onefile \
  --noconsole \
  --collect-data drohnendesign \
  drohnendesign/ui.py
