#!/bin/bash
# Send a Claude Code notification to a Discord channel via webhook.
# Requires DISCORD_WEBHOOK_URL to be set in your environment.
# Dependencies: curl, jq

if [[ -z "$DISCORD_WEBHOOK_URL" ]]; then
    exit 0
fi

input="$(cat)"

machine="$(hostname -s)"
msg="$(echo "$input" | jq -r '.message // "Claude Code needs your attention"')"
title="$(echo "$input" | jq -r '.title // empty')"
cwd="$(echo "$input" | jq -r '.cwd // empty')"
ntype="$(echo "$input" | jq -r '.notification_type // ""')"

case "$ntype" in
    idle_prompt)        color=8142317;  icon="💤"; default_title="Waiting for input" ;;
    permission_prompt)  color=16031371; icon="🔐"; default_title="Permission needed" ;;
    auth_success)       color=1097857;  icon="✅"; default_title="Authentication successful" ;;
    elicitation_dialog) color=3899902;  icon="💬"; default_title="Input needed" ;;
    *)                  color=8142317;  icon="🤖"; default_title="Notification" ;;
esac

[[ -z "$title" ]] && title="$default_title"
timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

embed="$(jq -n \
    --argjson color "$color" \
    --arg author "$icon $machine" \
    --arg title "$title" \
    --arg desc "$msg" \
    --arg ts "$timestamp" \
    '{color: $color, author: {name: $author}, title: $title, description: $desc, timestamp: $ts}')"

if [[ -n "$cwd" ]]; then
    embed="$(echo "$embed" | jq --arg cwd "📁 $cwd" '. + {footer: {text: $cwd}}')"
fi

payload="$(jq -n --argjson embed "$embed" '{username: "Claude Code", embeds: [$embed]}')"

curl -s -o /dev/null \
    -H "Content-Type: application/json" \
    -X POST \
    -d "$payload" \
    "$DISCORD_WEBHOOK_URL"
