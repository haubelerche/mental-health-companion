#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# One-time setup for Google Cloud Run deployment
# Project: ai20k030  |  Region: asia-southeast1
#
# Run this ONCE before your first deployment:
#   bash setup_cloudrun.sh
# ─────────────────────────────────────────────────────────────────────────────
set -eu

# ── Resolve gcloud on Windows Git Bash ────────────────────────────────────
_GCLOUD_WIN_PATH="/c/Users/Admin/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin"
if ! command -v gcloud &>/dev/null; then
  if [ -d "$_GCLOUD_WIN_PATH" ]; then
    export PATH="$_GCLOUD_WIN_PATH:$PATH"
    echo "(Added gcloud to PATH from: $_GCLOUD_WIN_PATH)"
  else
    echo "ERROR: gcloud not found. Install Google Cloud SDK from https://cloud.google.com/sdk/docs/install"
    exit 1
  fi
fi

PROJECT_ID="ai20k030"
REGION="asia-southeast1"

echo "==> Authenticating with Google Cloud..."
gcloud config set project "$PROJECT_ID"

echo "==> Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  --project="$PROJECT_ID"

echo "==> Creating Artifact Registry repository..."
gcloud artifacts repositories create serene \
  --repository-format=docker \
  --location="$REGION" \
  --description="Serene app Docker images" \
  --project="$PROJECT_ID" \
  || echo "(repository may already exist, continuing)"

echo ""
echo "==> Creating Secret Manager secrets from .env file..."
echo "    (Reads values from your local .env)"
echo ""

# Helper: create or update a secret
upsert_secret() {
  local name="$1"
  local value="$2"
  if gcloud secrets describe "$name" --project="$PROJECT_ID" &>/dev/null; then
    echo "  Updating secret: $name"
    echo -n "$value" | gcloud secrets versions add "$name" --data-file=- --project="$PROJECT_ID"
  else
    echo "  Creating secret: $name"
    echo -n "$value" | gcloud secrets create "$name" --data-file=- --project="$PROJECT_ID"
  fi
}

# Load .env safely using Python — handles spaces, multi-line JWT keys, CRLF
if [ ! -f ".env" ]; then
  echo "ERROR: .env file not found. Run from repo root."
  exit 1
fi

dotenv_get() {
  python3 - "$1" <<'PYEOF'
import sys, re

key = sys.argv[1]
content = open('.env', 'r', encoding='utf-8', errors='replace').read()
# Normalise CRLF → LF
content = content.replace('\r\n', '\n').replace('\r', '\n')

# Multi-line: KEY="......" (the value spans multiple lines inside double quotes)
m = re.search(r'^' + re.escape(key) + r'\s*=\s*"([\s\S]*?)"', content, re.MULTILINE)
if m:
    sys.stdout.write(m.group(1))
    sys.exit(0)

# Single-line: KEY=value or KEY="value"
m = re.search(r'^' + re.escape(key) + r'\s*=\s*([^\n]+)', content, re.MULTILINE)
if m:
    val = m.group(1).strip()
    if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
        val = val[1:-1]
    elif len(val) >= 2 and val[0] == "'" and val[-1] == "'":
        val = val[1:-1]
    sys.stdout.write(val)
PYEOF
}

DATABASE_URL=$(dotenv_get "DATABASE_URL")
OPENAI_API_KEY=$(dotenv_get "OPENAI_API_KEY")
JWT_PRIVATE_KEY=$(dotenv_get "JWT_PRIVATE_KEY")
JWT_PUBLIC_KEY=$(dotenv_get "JWT_PUBLIC_KEY")
CSRF_TRUSTED_ORIGINS=$(dotenv_get "CSRF_TRUSTED_ORIGINS")
ADMIN_LOGIN_EMAIL=$(dotenv_get "ADMIN_LOGIN_EMAIL")
ADMIN_PASSWORD_HASH=$(dotenv_get "ADMIN_PASSWORD_HASH")
ADMIN_TOTP_SECRET=$(dotenv_get "ADMIN_TOTP_SECRET")
EXA_API_KEY=$(dotenv_get "EXA_API_KEY")

FRONTEND_URL_PLACEHOLDER="https://serene-frontend-PLACEHOLDER.a.run.app"
BACKEND_URL_PLACEHOLDER="https://serene-backend-PLACEHOLDER.a.run.app"
ALL_ORIGINS="${CSRF_TRUSTED_ORIGINS},${FRONTEND_URL_PLACEHOLDER},${BACKEND_URL_PLACEHOLDER}"

upsert_secret "serene-database-url"         "$DATABASE_URL"
upsert_secret "serene-openai-api-key"       "$OPENAI_API_KEY"
upsert_secret "serene-jwt-private-key"      "$JWT_PRIVATE_KEY"
upsert_secret "serene-jwt-public-key"       "$JWT_PUBLIC_KEY"
upsert_secret "serene-csrf-origins"         "$ALL_ORIGINS"
upsert_secret "serene-admin-email"          "$ADMIN_LOGIN_EMAIL"
upsert_secret "serene-admin-password-hash"  "$ADMIN_PASSWORD_HASH"
upsert_secret "serene-admin-totp-secret"    "$ADMIN_TOTP_SECRET"
upsert_secret "serene-exa-api-key"          "$EXA_API_KEY"

echo ""
echo "==> Granting Cloud Build service account access to secrets..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
CR_SA="service-${PROJECT_NUMBER}@serverless-robot-prod.iam.gserviceaccount.com"

for sa in "$CB_SA" "$CR_SA"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${sa}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    --quiet || true
done

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/run.admin" \
  --condition=None \
  --quiet || true

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/iam.serviceAccountUser" \
  --condition=None \
  --quiet || true

echo ""
echo "==> Connecting Cloud Build to this Git repo..."
echo "    Go to: https://console.cloud.google.com/cloud-build/triggers?project=${PROJECT_ID}"
echo "    Create a trigger pointing to this repo, using cloudbuild.yaml"
echo ""
echo "✅ Setup complete! Now run: bash deploy.sh"
