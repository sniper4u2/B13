#!/bin/bash
###############################################################################
# B13 Agent - Kaggle Push Script (uses venv CLI credentials)
# Account: jhonmccarty | SFT data already at jhonmccarty/b13-cybersecurity-datasets
###############################################################################
set -euo pipefail

KAGGLE_USERNAME="jhonmccarty"
PROJECT_ROOT="/home/b13/Desktop/b13 agent"
KAGGLE_DIR="${PROJECT_ROOT}/b13_agent/training/kaggle"
STAGING_DIR="${PROJECT_ROOT}/.kaggle_push"
CODE_STAGING="${STAGING_DIR}/b13-agent-code"

# Use the venv's kaggle credentials + CLI (proven working)
export KAGGLE_CONFIG_DIR="${PROJECT_ROOT}/training_environment/venv/etc/kaggle"
VENV_KAGGLE="${PROJECT_ROOT}/training_environment/venv/bin/kaggle"
if [ -x "${VENV_KAGGLE}" ]; then KG="${VENV_KAGGLE}"; else KG="kaggle"; fi

echo "============================================================"
echo "  B13 Agent - Kaggle Push (PRIVATE) | Account: ${KAGGLE_USERNAME}"
echo "============================================================"

rm -rf "${STAGING_DIR}"
mkdir -p "${CODE_STAGING}/b13_agent/tools" "${CODE_STAGING}/b13_agent/b13/cybersecurity" "${CODE_STAGING}/b13_agent/training/kaggle"

# --- 1. Package LEAN code ---
echo "[1/3] Packaging lean b13_agent code..."
cp "${PROJECT_ROOT}/b13_agent/__init__.py"            "${CODE_STAGING}/b13_agent/"
cp "${PROJECT_ROOT}/b13_agent/agent.py"               "${CODE_STAGING}/b13_agent/"
cp "${PROJECT_ROOT}/b13_agent/runtime.py"             "${CODE_STAGING}/b13_agent/"
cp "${PROJECT_ROOT}/b13_agent/ui.py"                  "${CODE_STAGING}/b13_agent/"
cp "${PROJECT_ROOT}/b13_agent/tools/"*.py             "${CODE_STAGING}/b13_agent/tools/"
cp "${PROJECT_ROOT}/b13_agent/b13/__init__.py"        "${CODE_STAGING}/b13_agent/b13/"
cp "${PROJECT_ROOT}/b13_agent/b13/runtime.py"         "${CODE_STAGING}/b13_agent/b13/"
cp "${PROJECT_ROOT}/b13_agent/b13/cybersecurity/"*.py  "${CODE_STAGING}/b13_agent/b13/cybersecurity/"
cp "${KAGGLE_DIR}/train_agent_kaggle.py"              "${CODE_STAGING}/b13_agent/training/kaggle/"
cp "${KAGGLE_DIR}/requirements_kaggle.txt"            "${CODE_STAGING}/"
echo "b13" > "${CODE_STAGING}/AGENT_NAME"
echo "  Lean code size: $(du -sh "${CODE_STAGING}" | cut -f1)"

# --- 2. Create/update PRIVATE code dataset ---
echo "[2/3] Syncing PRIVATE code dataset (${KAGGLE_USERNAME}/b13-agent-code)..."
cp "${KAGGLE_DIR}/dataset-metadata-code.json" "${CODE_STAGING}/dataset-metadata.json"
if "${KG}" datasets status "${KAGGLE_USERNAME}/b13-agent-code" >/dev/null 2>&1; then
    echo "  Exists - new version..."
    "${KG}" datasets version -p "${CODE_STAGING}" -m "Update B13 agent code" --dir-mode zip --delete-old-versions
else
    echo "  Creating new PRIVATE dataset..."
    "${KG}" datasets create -p "${CODE_STAGING}" --dir-mode zip
fi

# --- 3. Push PRIVATE kernel ---
echo "[3/3] Pushing PRIVATE kernel (${KAGGLE_USERNAME}/b13-agent-tpu-training)..."
cp "${KAGGLE_DIR}/train_b13_agent_kaggle.ipynb" "${STAGING_DIR}/"
cp "${KAGGLE_DIR}/kernel-metadata.json" "${STAGING_DIR}/"
if "${KG}" kernels status "${KAGGLE_USERNAME}/b13-agent-tpu-training" >/dev/null 2>&1; then
    echo "  Exists - new version..."
    "${KG}" kernels push -p "${STAGING_DIR}"
else
    echo "  Creating new PRIVATE kernel..."
    "${KG}" kernels push -p "${STAGING_DIR}"
fi

echo "============================================================"
echo "  DONE. Code: ${KAGGLE_USERNAME}/b13-agent-code (PRIVATE)"
echo "  Kernel: ${KAGGLE_USERNAME}/b13-agent-tpu-training (PRIVATE)"
echo "  Data: ${KAGGLE_USERNAME}/b13-cybersecurity-datasets (exists)"
echo "  Run kernel with TPU-v3-8 accelerator."
echo "============================================================"
