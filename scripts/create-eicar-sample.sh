#!/usr/bin/env bash
set -euo pipefail

OUTPUT="${1:-/tmp/eicar.com.txt}"
# Harmless industry-standard AV test string. It is assembled at runtime so the
# project archive and container image do not contain the complete signature.
printf '%s%s%s' \
  'X5O!P%@AP[4\PZX54(P^)7CC)7}' \
  '$EICAR-STANDARD-' \
  'ANTIVIRUS-TEST-FILE!$H+H*' > "$OUTPUT"
printf 'Created harmless EICAR test file: %s\n' "$OUTPUT"
