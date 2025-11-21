#!/bin/sh
set -e

# Replace placeholders in Next.js static files with runtime env vars
replace_placeholder() {
  find /app/.next/static -type f -exec sed -i "s|$1|$2|g" {} +
}

replace_placeholder "__API_GATEWAY_URL__" "${NEXT_PUBLIC_API_GATEWAY_URL}"

exec "$@"
