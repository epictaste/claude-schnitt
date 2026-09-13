#!/usr/bin/env bash
# SessionStart hook for /cut. One line when something is missing, silence when
# everything is in place, so it never becomes noise.
set -euo pipefail

CONFIG_FILE="$HOME/.config/cut/.env"
FALLBACK_FILE="$HOME/.config/watch/.env"

for file in "$CONFIG_FILE" "$FALLBACK_FILE"; do
  [[ -f "$file" ]] || continue
  perms=$(stat -c '%a' "$file" 2>/dev/null || stat -f '%Lp' "$file" 2>/dev/null || echo "")
  if [[ -n "$perms" && "$perms" != "600" && "$perms" != "400" ]]; then
    echo "/cut: WARNING - $file has permissions $perms (should be 600). Fix: chmod 600 $file"
  fi
done

read_key() {
  local name="$1" file="$2"
  [[ -f "$file" ]] || return 0
  awk -F= -v k="$name" '
    /^[[:space:]]*#/ { next }
    $1 == k {
      sub(/^[[:space:]]*/, "", $2); sub(/[[:space:]]*$/, "", $2);
      gsub(/^["'\'']|["'\'']$/, "", $2);
      if ($2 != "") { print $2; exit }
    }
  ' "$file"
}

MISSING=""
for binary in ffmpeg ffprobe node npm; do
  command -v "$binary" >/dev/null 2>&1 || MISSING="$MISSING $binary"
done

KEY="${DEEPGRAM_API_KEY:-}"
[[ -n "$KEY" ]] || KEY="$(read_key DEEPGRAM_API_KEY "$CONFIG_FILE")"
[[ -n "$KEY" ]] || KEY="$(read_key DEEPGRAM_API_KEY "$FALLBACK_FILE")"

if [[ -n "$MISSING" ]]; then
  echo "/cut: needs$MISSING. Run: python3 \$CLAUDE_PLUGIN_ROOT/skills/cut/scripts/setup.py"
elif [[ -z "$KEY" ]]; then
  echo "/cut: needs a Deepgram API key for word-level timestamps. Add DEEPGRAM_API_KEY to $CONFIG_FILE (console.deepgram.com)."
fi

exit 0
