#!/bin/bash

# starting the script in secure mode
set -euo pipefail

# start Ollama and save the process PID
ollama serve & OLLAMA_PID=$!

# wait till the API is responsive, quitting if isnt
READY=false
for _ in $(seq 1 60); do
    if ollama list >/dev/null 2>&1; then
        READY=true
        break
    fi
    sleep 1
done
if [ "$READY" = false ]; then
    echo "Ollama failed to start."
    exit 1
fi

# read the envinroment variable
MODELS="${OLLAMA_MODELS:-llama3}"

# dividing the model pullings
IFS=',' read -ra REQUESTED <<< "$MODELS"

# loop in the models
for model in "${REQUESTED[@]}"; do
    trimmed="$(echo "$model" | xargs)"
    if [ -n "$trimmed" ]; then
        echo "[pull-models] Pulling ${trimmed} ..."
        ollama pull "$trimmed"
    fi
done

# waiting the existing activities in the process
echo "[pull-models] all requested models are present. Ollama keeps running."
wait "$OLLAMA_PID"
