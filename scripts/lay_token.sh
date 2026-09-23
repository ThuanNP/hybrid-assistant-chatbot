#!/usr/bin/env bash
# ==============================================================================
# scripts/lay_token.sh - Lấy access token từ endpoint /api/v1/dang-nhap
# Sử dụng: TOKEN=$(bash scripts/lay_token.sh <email> <mat_khau>)
# Không dùng jq; trích xuất JSON bằng python -c qua uv run --frozen từ backend/.
# ==============================================================================
set -euo pipefail

EMAIL="${1:-}"
MAT_KHAU="${2:-}"

if [ -z "$EMAIL" ] || [ -z "$MAT_KHAU" ]; then
  echo "Lỗi: Thiếu tham số. Cách dùng: bash scripts/lay_token.sh <email> <mat_khau>" >&2
  exit 1
fi

THU_MUC_GOC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PHAN_HOI=$(curl -s -X POST http://localhost:8000/api/v1/dang-nhap \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"mat_khau\":\"$MAT_KHAU\"}")

TOKEN=$(cd "$THU_MUC_GOC/backend" && uv run --frozen python -c "
import sys, json
try:
    du_lieu = json.loads(sys.argv[1])
    token = du_lieu.get('access_token', '')
    if token:
        print(token)
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
" "$PHAN_HOI")

echo "$TOKEN"
