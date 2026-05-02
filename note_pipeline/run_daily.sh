#!/bin/bash
# Daily note.com article pipeline runner
# Called via cron at 8:00 JST daily (23:00 UTC)

# Load API key from credentials file
CREDS_FILE="/home/agena/claude_org/agenta/credentials/anthropic.md"
if [ -f "$CREDS_FILE" ]; then
    export ANTHROPIC_API_KEY=$(grep -oP '(?<=\*\*API Key\*\*: )sk-ant-[^\s]+' "$CREDS_FILE")
fi

PIPELINE_DIR="/home/agena/claude_org/ventures/execution/note_pipeline"
cd "$PIPELINE_DIR" && python3 daily_pipeline.py >> /home/agena/claude_org/ventures/logs/note_daily.log 2>&1
