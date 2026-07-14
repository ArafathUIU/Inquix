#!/bin/bash
# Run once to pre-pull models
docker compose up -d ollama
echo "Waiting for Ollama to be ready..."
for i in $(seq 1 30); do
  if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama is ready."
    break
  fi
  sleep 2
done
echo "Pulling nomic-embed-text..."
docker compose exec ollama ollama pull nomic-embed-text
echo "Pulling qwen2.5:3b..."
docker compose exec ollama ollama pull qwen2.5:3b
echo "Done. Models cached."
docker compose down ollama
