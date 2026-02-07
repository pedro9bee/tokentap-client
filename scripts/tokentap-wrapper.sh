#!/usr/bin/env bash
#
# Tokentap Context Wrapper
# Injects context metadata (program, project, tags) into LLM API calls via environment
#
# Usage:
#   tokentap-wrapper.sh <program-name> <command> [args...]
#
# Examples:
#   tokentap-wrapper.sh "my-script" claude
#   tokentap-wrapper.sh "automation-bot" python bot.py
#   TOKENTAP_PROJECT="my-project" tokentap-wrapper.sh "test" npm run dev
#
# Environment Variables (optional):
#   TOKENTAP_PROJECT   - Project/workspace name (default: current directory name)
#   TOKENTAP_SESSION   - Session identifier (default: process ID)
#   TOKENTAP_TAGS      - JSON array of tags (e.g., ["experimental", "debug"])
#   TOKENTAP_CONTEXT   - Full JSON context (merged with other vars)

set -euo pipefail

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <program-name> <command> [args...]"
    echo ""
    echo "Examples:"
    echo "  $0 \"my-script\" claude"
    echo "  $0 \"automation\" python bot.py"
    echo "  TOKENTAP_PROJECT=\"proj\" $0 \"test\" npm run dev"
    echo ""
    echo "Environment Variables:"
    echo "  TOKENTAP_PROJECT   - Project name (default: current dir)"
    echo "  TOKENTAP_SESSION   - Session ID (default: $$)"
    echo "  TOKENTAP_TAGS      - JSON array of tags"
    echo "  TOKENTAP_CONTEXT   - Full JSON context"
    exit 1
fi

# Extract program name
PROGRAM_NAME="$1"
shift

# Build context JSON
PROJECT_NAME="${TOKENTAP_PROJECT:-$(basename "$(pwd)")}"
SESSION_ID="${TOKENTAP_SESSION:-$$}"
TAGS="${TOKENTAP_TAGS:-[]}"

# Base context
CONTEXT=$(cat <<EOF
{
  "program_name": "$PROGRAM_NAME",
  "project_name": "$PROJECT_NAME",
  "session_id": "$SESSION_ID",
  "tags": $TAGS
}
EOF
)

# Merge with existing TOKENTAP_CONTEXT if provided
if [ -n "${TOKENTAP_CONTEXT:-}" ]; then
    # Use jq to merge if available, otherwise just use custom context
    if command -v jq >/dev/null 2>&1; then
        CONTEXT=$(echo "$CONTEXT" | jq -s '.[0] * (env.TOKENTAP_CONTEXT | fromjson)' 2>/dev/null || echo "$CONTEXT")
    fi
fi

# Export context for proxy to pickup via header injection
# Note: This works if the CLI tool supports custom headers via env vars
# For tools that don't, context will be inferred from User-Agent
export TOKENTAP_CONTEXT="$CONTEXT"

# Optional: Set custom headers if the tool supports it
# Some SDKs check for HTTP_EXTRA_HEADERS or similar
export HTTP_EXTRA_HEADERS=$(cat <<EOF
{"X-Tokentap-Context": $CONTEXT}
EOF
)

# Run the command with all remaining arguments
exec "$@"
