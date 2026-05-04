#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Manual deployment script — runs Cloud Build pipeline locally
# Project: ai20k030  |  Region: asia-southeast1
#
# Usage:
#   bash deploy.sh            # deploy current HEAD
#   bash deploy.sh --backend  # deploy backend only
#   bash deploy.sh --frontend # deploy frontend only (requires backend already deployed)
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
BACKEND_SERVICE="serene-backend"
FRONTEND_SERVICE="serene-frontend"
REPO="$REGION-docker.pkg.dev/$PROJECT_ID/serene"
TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "manual")

MODE="${1:-all}"

echo "================================================"
echo " Serene — Cloud Run Deployment"
echo " Project  : $PROJECT_ID"
echo " Region   : $REGION"
echo " Commit   : $TAG"
echo " Mode     : $MODE"
echo "================================================"

gcloud config set project "$PROJECT_ID"
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

# ── Backend ────────────────────────────────────────────────────────────────
deploy_backend() {
  echo ""
  echo "==> Building backend image..."
  docker build -t "$REPO/backend:$TAG" -t "$REPO/backend:latest" ./backend

  echo "==> Pushing backend image..."
  docker push "$REPO/backend:$TAG"
  docker push "$REPO/backend:latest"

  echo "==> Deploying backend to Cloud Run..."
  gcloud run deploy "$BACKEND_SERVICE" \
    --image="$REPO/backend:$TAG" \
    --region="$REGION" \
    --platform=managed \
    --allow-unauthenticated \
    --min-instances=0 \
    --max-instances=10 \
    --memory=1Gi \
    --cpu=1 \
    --timeout=120s \
    --set-secrets="DATABASE_URL=serene-database-url:latest,OPENAI_API_KEY=serene-openai-api-key:latest,JWT_PRIVATE_KEY=serene-jwt-private-key:latest,JWT_PUBLIC_KEY=serene-jwt-public-key:latest,CSRF_TRUSTED_ORIGINS=serene-csrf-origins:latest,ADMIN_LOGIN_EMAIL=serene-admin-email:latest,ADMIN_PASSWORD_HASH=serene-admin-password-hash:latest,ADMIN_TOTP_SECRET=serene-admin-totp-secret:latest,EXA_API_KEY=serene-exa-api-key:latest" \
    --set-env-vars="APP_NAME=Serene API,APP_VERSION=1.0.0,API_PREFIX=/v1,AUTO_CREATE_SCHEMA=false,COOKIE_SECURE=true,JWT_ALGORITHM=RS256,LOG_LEVEL=INFO,DEFAULT_MODEL=gpt-4o-mini"

  BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" \
    --region="$REGION" \
    --format='value(status.url)')
  echo "  Backend URL: $BACKEND_URL"
  echo -n "$BACKEND_URL" > /tmp/serene_backend_url.txt
}

# ── Frontend ───────────────────────────────────────────────────────────────
deploy_frontend() {
  if [ -f /tmp/serene_backend_url.txt ]; then
    BACKEND_URL=$(cat /tmp/serene_backend_url.txt)
  else
    BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" \
      --region="$REGION" \
      --format='value(status.url)' 2>/dev/null || echo "")
    if [ -z "$BACKEND_URL" ]; then
      echo "ERROR: Backend not deployed yet. Run: bash deploy.sh --backend first."
      exit 1
    fi
  fi

  echo ""
  echo "==> Building frontend image (backend: $BACKEND_URL)..."
  docker build -t "$REPO/frontend:$TAG" -t "$REPO/frontend:latest" ./frontend

  echo "==> Pushing frontend image..."
  docker push "$REPO/frontend:$TAG"
  docker push "$REPO/frontend:latest"

  echo "==> Deploying frontend to Cloud Run..."
  gcloud run deploy "$FRONTEND_SERVICE" \
    --image="$REPO/frontend:$TAG" \
    --region="$REGION" \
    --platform=managed \
    --allow-unauthenticated \
    --min-instances=0 \
    --max-instances=5 \
    --memory=256Mi \
    --cpu=1 \
    --timeout=60s \
    --set-env-vars="BACKEND_URL=$BACKEND_URL"

  FRONTEND_URL=$(gcloud run services describe "$FRONTEND_SERVICE" \
    --region="$REGION" \
    --format='value(status.url)')
  echo "  Frontend URL: $FRONTEND_URL"
}

# ── Run ────────────────────────────────────────────────────────────────────
case "$MODE" in
  --backend)
    deploy_backend
    ;;
  --frontend)
    deploy_frontend
    ;;
  *)
    deploy_backend
    deploy_frontend
    ;;
esac

echo ""
echo "================================================"
echo " ✅ Deployment complete!"
if [ -f /tmp/serene_backend_url.txt ]; then
  echo " Backend  : $(cat /tmp/serene_backend_url.txt)"
fi
FRONTEND_URL=$(gcloud run services describe "$FRONTEND_SERVICE" \
  --region="$REGION" \
  --format='value(status.url)' 2>/dev/null || echo "not deployed")
echo " Frontend : $FRONTEND_URL"
echo "================================================"
echo ""
echo "Next steps:"
echo "  1. Update CSRF_TRUSTED_ORIGINS in Secret Manager to include the frontend URL above"
echo "     bash setup_cloudrun.sh   (re-run after updating .env CSRF_TRUSTED_ORIGINS)"
echo "  2. Visit: $FRONTEND_URL"
