#!/bin/sh
# Script to generate secureboot keys
set -e

DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

openssl req -newkey rsa:4096 -nodes -keyout "${DIR}/mok.key" \
    -new -x509 -sha256 -days 3650 \
    -subj "/CN=Machine Owner Key/" \
    -out "${DIR}/mok.crt"

openssl x509 -outform DER -in "${DIR}/mok.crt" -out "${DIR}/mok.cer"
