#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN=${PYTHON_BIN:-python3}

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Error: ${PYTHON_BIN} is not installed. Install Python 3.9+ and retry." >&2
  exit 1
fi

if [ ! -d "${VENV_DIR}" ]; then
  echo "Creating virtual environment in ${VENV_DIR}";
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r "${ROOT_DIR}/requirements.txt"

cat <<INSTRUCTIONS

Environment ready! To start using the toolkit run:

  source "${VENV_DIR}/bin/activate"
  PYTHONPATH="${ROOT_DIR}" python -m takeoff.cli --trade concrete --input construction_takeoff/docs --output estimate.csv

To launch the UI:

  source "${VENV_DIR}/bin/activate"
  PYTHONPATH="${ROOT_DIR}" uvicorn takeoff.webapp.app:create_app --reload

INSTRUCTIONS
