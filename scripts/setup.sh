#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_DIR="${HOME}/.claude"
SETTINGS="${CLAUDE_DIR}/settings.json"
HOOK_TARGET='${HOME}/.claude/notify-discord.sh'

mkdir -p "$CLAUDE_DIR"

cp "$REPO_DIR/scripts/notify-discord.sh" "$CLAUDE_DIR/notify-discord.sh"
chmod +x "$CLAUDE_DIR/notify-discord.sh"
echo "Installed notify-discord.sh -> $CLAUDE_DIR/notify-discord.sh"

if [[ ! -f "$SETTINGS" ]]; then
    echo '{}' > "$SETTINGS"
fi

updated="$(jq --arg cmd "$HOOK_TARGET" '
    .hooks.Notification //= [] |
    reduce ("idle_prompt", "permission_prompt", "auth_success", "elicitation_dialog") as $m (
        .;
        if any(.hooks.Notification[]; .matcher == $m and any(.hooks[]; .command == $cmd))
        then .
        elif any(.hooks.Notification[]; .matcher == $m)
        then .hooks.Notification = [
            .hooks.Notification[] |
            if .matcher == $m
            then .hooks += [{"type": "command", "command": $cmd}]
            else .
            end
        ]
        else .hooks.Notification += [{"matcher": $m, "hooks": [{"type": "command", "command": $cmd}]}]
        end
    )
' "$SETTINGS")"

echo "$updated" > "$SETTINGS"
echo "Registered Discord notification hook for all notification types in $SETTINGS"
