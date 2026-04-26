#!/bin/sh
set -e

# Default port for Cloud Run
export PORT="${PORT:-8080}"

# Substitute only BACKEND_URL and PORT; all other $var in nginx config are left as-is
envsubst '${BACKEND_URL} ${PORT}' \
  < /etc/nginx/nginx.conf.template \
  > /etc/nginx/conf.d/default.conf

# Remove the default nginx welcome page config if it exists
rm -f /etc/nginx/conf.d/default.conf.bak

exec "$@"
