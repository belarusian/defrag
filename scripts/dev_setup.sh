#!/usr/bin/env bash
# Developer convenience script for preparing a local defrag environment.

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/dev_setup.sh [VENV_DIR]

Sets up a virtual environment (default: .venv) and installs defrag with dev extras.

Examples:
  scripts/dev_setup.sh           # create/use .venv
  scripts/dev_setup.sh .my-venv  # specify venv directory
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

VENV_DIR="${1:-.venv}"

if [[ ! -d "${VENV_DIR}" ]]; then
    echo "Creating virtual environment at ${VENV_DIR}..."
    python3 -m venv "${VENV_DIR}"
else
    echo "Using existing virtual environment at ${VENV_DIR}."
fi

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

echo "Upgrading pip..."
pip install --upgrade pip >/dev/null

echo "Installing defrag in editable mode with dev extras..."
pip install -e ".[dev]"

cat <<EOF

Done! Virtual environment ready at ${VENV_DIR}.

Activate it before working on defrag:
  source ${VENV_DIR}/bin/activate

Configure an LLM provider (one of):
  export ANTHROPIC_API_KEY=your_key_here
  # or
  export DEFRAG_LLM_PROVIDER=openai
  export OPENAI_API_KEY=your_key_here

Happy hacking!
EOF
