#!/usr/bin/env bash
# SessionStart-Hook für /schnitt. Eine Zeile, wenn etwas fehlt, sonst still.
set -euo pipefail

CONFIG_FILE="$HOME/.config/schnitt/.env"
FALLBACK_FILE="$HOME/.config/watch/.env"
VENV_PY="$HOME/.config/schnitt/venv/bin/python"

for file in "$CONFIG_FILE" "$FALLBACK_FILE"; do
  [[ -f "$file" ]] || continue
  perms=$(stat -c '%a' "$file" 2>/dev/null || stat -f '%Lp' "$file" 2>/dev/null || echo "")
  if [[ -n "$perms" && "$perms" != "600" && "$perms" != "400" ]]; then
    echo "/schnitt: WARNUNG, $file hat die Rechte $perms (sollte 600 sein). Beheben: chmod 600 $file"
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

SETUP="python3 \${CLAUDE_PLUGIN_ROOT}/skills/schnitt/scripts/setup.py"
if [[ -n "$MISSING" ]]; then
  echo "/schnitt: es fehlt$MISSING. Ausführen: $SETUP"
elif [[ ! -x "$VENV_PY" ]]; then
  echo "/schnitt: Einrichtung noch nicht gelaufen. Ausführen: $SETUP"
elif [[ -z "$KEY" ]]; then
  echo "/schnitt: Deepgram-Key fehlt (für die Wortzeiten). DEEPGRAM_API_KEY in $CONFIG_FILE eintragen (console.deepgram.com)."
fi

exit 0
