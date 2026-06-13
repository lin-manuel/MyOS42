#!/usr/bin/env bash
set -euo pipefail

npm install
npx tailwindcss -i ./myos_app/static/css/tailwind.input.css -o ./myos_app/static/css/tailwind.min.css --minify
python3 manage.py collectstatic --noinput
