set -e

ZIP_NAME="tap_sources_$(date +%Y%m%d_%H%M%S).zip"

echo "Creating $ZIP_NAME ..."

zip -r "$ZIP_NAME" \
  backend \
  frontend \
  configs \
  scripts \
  docker-compose.yml \
  Dockerfile \
  package.json \
  pnpm-lock.yaml \
  package-lock.json \
  yarn.lock \
  requirements.txt \
  pyproject.toml \
  README.md \
  .env.example \
  -x \
  "*/node_modules/*" \
  "*/venv/*" \
  "*/.venv/*" \
  "*/__pycache__/*" \
  "*/.pytest_cache/*" \
  "*/.mypy_cache/*" \
  "*/.git/*" \
  "*/dist/*" \
  "*/build/*" \
  "*/.next/*" \
  "*/logs/*" \
  "*/wandb/*" \
  "*/checkpoints/*" \
  "*/artifacts/*" \
  "*/data/*" \
  "*.db" \
  "*.sqlite" \
  "*.sqlite3" \
  ".env" \
  "*.key" \
  "*.pem"

echo "Done: $ZIP_NAME"