#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/opt/homebrew/opt/python@3.12/libexec/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "Could not find Python. Install Python 3.12 with Tk support first."
  exit 1
fi

"$PYTHON_BIN" -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r app/requirements.txt
python - <<'PY'
import _tkinter

print(f"Using Tk from {_tkinter.__file__}")
PY

python app/make_icon.py
iconutil -c icns app/assets/AppIcon.iconset -o app/assets/AppIcon.icns

pyinstaller --clean --noconfirm app/rj.spec
SIGN_IDENTITY="${SIGN_IDENTITY:--}" scripts/sign_macos_app.sh

echo "Built dist/RJ.app"
