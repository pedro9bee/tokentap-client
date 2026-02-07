# Context Metadata and Program Tracking

Tokentap can capture additional context about who/what called the LLM API, enabling you to:

- Track token usage by program/script
- Analyze usage by project/workspace
- Group requests by session or experiment
- Add custom tags for categorization

## Quick Start

```bash
# Method 1: Environment variables
export TOKENTAP_PROJECT="my-project"
export TOKENTAP_CONTEXT='{"experiment":"v2","user":"alice"}'
claude

# Method 2: Wrapper script
./scripts/tokentap-wrapper.sh "my-automation-script" claude

# Method 3: Manual headers (advanced)
export HTTP_EXTRA_HEADERS='{"X-Tokentap-Context":"{\"program\":\"bot\"}"}'
```

## Context Fields

All events in MongoDB include a `context` object:

```json
{
  "context": {
    "program_name": "my-script",
    "project_name": "my-project",
    "session_id": "12345",
    "tags": ["experimental", "debug"],
    "custom": {
      "experiment": "v2",
      "branch": "feature-x"
    }
  },
  "program": "my-script",    // Top-level shortcut
  "project": "my-project"     // Top-level shortcut
}
```

## Usage Methods

### Method 1: Environment Variables

Simple and CLI-friendly:

```bash
# Set project
export TOKENTAP_PROJECT="my-project"

# Set custom context (JSON)
export TOKENTAP_CONTEXT='{"experiment":"test-v2","branch":"main"}'

# Run your LLM tool
claude "Write a hello world program"
```

**How it works**: The proxy checks for these environment variables (if exposed) or looks for `X-Tokentap-Context` headers.

### Method 2: Wrapper Script

Use `tokentap-wrapper.sh` for automatic context injection:

```bash
# Basic usage
./scripts/tokentap-wrapper.sh "my-script-name" claude

# With project
TOKENTAP_PROJECT="analytics" ./scripts/tokentap-wrapper.sh "daily-report" python report.py

# With tags
TOKENTAP_TAGS='["automated","daily"]' ./scripts/tokentap-wrapper.sh "cron-job" python task.py
```

**Script syntax**:
```bash
tokentap-wrapper.sh <program-name> <command> [args...]
```

**Environment variables** (optional):
- `TOKENTAP_PROJECT` - Project/workspace name (default: current dir)
- `TOKENTAP_SESSION` - Session identifier (default: process ID)
- `TOKENTAP_TAGS` - JSON array of tags
- `TOKENTAP_CONTEXT` - Full JSON context (merged with others)

### Method 3: HTTP Headers (Advanced)

For tools that support custom HTTP headers:

```bash
export HTTP_EXTRA_HEADERS='{"X-Tokentap-Context": "{\"program\":\"my-bot\",\"project\":\"automation\"}"}'
claude
```

Or set headers directly in your SDK code:

```python
# Python SDK example
import anthropic

client = anthropic.Anthropic(
    default_headers={
        "X-Tokentap-Program": "my-script",
        "X-Tokentap-Project": "my-project",
    }
)
```

## Supported Headers

The proxy recognizes these custom headers:

- `X-Tokentap-Program` - Program name
- `X-Tokentap-Project` - Project name
- `X-Tokentap-Session` - Session ID
- `X-Tokentap-Context` - Full JSON context (merged with other headers)

## Querying by Context

### Web Dashboard

Filter events by program, project, or tags in the web UI at `http://localhost:3000`.

### CLI

```bash
# Query MongoDB directly
docker exec -it tokentap-client-mongodb-1 mongosh tokentap

# Find events by program
db.events.find({"program": "my-script"})

# Find events by project
db.events.find({"project": "my-project"})

# Aggregate usage by program
db.events.aggregate([
  {$group: {
    _id: "$program",
    total_tokens: {$sum: "$total_tokens"},
    request_count: {$sum: 1}
  }},
  {$sort: {total_tokens: -1}}
])
```

### API

Tokentap web dashboard exposes REST endpoints:

```bash
# Usage by program
curl 'http://localhost:3000/api/stats/by-program'

# Usage by project
curl 'http://localhost:3000/api/stats/by-project'

# Filter by project
curl 'http://localhost:3000/api/events?project=my-project'
```

## Use Cases

### 1. Track Automated Scripts

```bash
#!/bin/bash
# daily-report.sh

./scripts/tokentap-wrapper.sh "daily-report" python generate_report.py

# Later query:
# db.events.find({program: "daily-report"})
```

### 2. A/B Testing Experiments

```bash
# Experiment A
export TOKENTAP_CONTEXT='{"experiment":"prompt-v1"}'
python test_prompts.py

# Experiment B
export TOKENTAP_CONTEXT='{"experiment":"prompt-v2"}'
python test_prompts.py

# Compare results:
# db.events.find({"context.custom.experiment": "prompt-v1"})
# db.events.find({"context.custom.experiment": "prompt-v2"})
```

### 3. Project-Level Tracking

```bash
# In project directory
export TOKENTAP_PROJECT="client-website"

# All LLM calls will be tagged with this project
claude "Generate SEO metadata"
codex "Refactor authentication"

# Query usage:
# db.events.find({project: "client-website"})
```

### 4. Multi-User Environments

```bash
# Each user sets their name
export TOKENTAP_CONTEXT='{"user":"alice","team":"backend"}'
claude

# Query usage by user:
# db.events.find({"context.custom.user": "alice"})
```

## Context Inference

If no context is provided, tokentap attempts to infer it from:

1. **User-Agent header**: Detects `claude-code`, `kiro-cli`, etc.
2. **Request host**: Maps to provider

This provides basic tracking even without explicit context.

## Example: Wrapper in Cron Jobs

```bash
# /etc/cron.daily/ai-report
#!/bin/bash

TOKENTAP_PROJECT="analytics" \
TOKENTAP_TAGS='["automated","cron"]' \
/path/to/tokentap-wrapper.sh "daily-ai-report" \
  python /path/to/generate_report.py
```

## Example: CI/CD Integration

```yaml
# .github/workflows/ai-review.yml
- name: AI Code Review
  env:
    TOKENTAP_PROJECT: "my-repo"
    TOKENTAP_CONTEXT: '{"ci":"github-actions","branch":"${{ github.ref }}"}'
  run: |
    ./scripts/tokentap-wrapper.sh "ai-code-review" \
      python review_pr.py
```

## MongoDB Schema

Events stored with context:

```json
{
  "timestamp": "2026-02-07T10:30:00Z",
  "provider": "anthropic",
  "model": "claude-sonnet-4",
  "input_tokens": 100,
  "output_tokens": 200,

  "context": {
    "program_name": "my-script",
    "project_name": "my-project",
    "session_id": "abc123",
    "tags": ["automated"],
    "custom": {
      "experiment": "v2"
    }
  },

  "program": "my-script",    // Denormalized for easier queries
  "project": "my-project"
}
```

## See Also

- [Provider Configuration](PROVIDER_CONFIGURATION.md)
- [Service Management](SERVICE_MANAGEMENT.md)
- [Debugging New Providers](DEBUGGING_NEW_PROVIDERS.md)
