# Daily Job Deployment Guide

## Overview

This document provides optional deployment instructions for running the OptiSigns OptiBot scraper as a scheduled daily job. The implementation is deployment-ready but was validated locally due to account constraints.

## Components

- **`main.py`**: Main entrypoint that orchestrates the daily job
- **`scrape.py`**: Scrapes articles from OptiSigns Zendesk API
- **`upload_vector_store.py`**: Uploads files to OpenAI Vector Store
- **`Dockerfile`**: Containerizes the application for deployment
- **`state.json`**: Tracks previously processed articles (auto-generated)
- **`vector_store_id.txt`**: Stores the Vector Store ID (auto-generated)

## How It Works

### Delta Detection

The job uses SHA-256 content hashing to detect changes:

1. **First Run**: All articles are new → uploads all to Vector Store
2. **Subsequent Runs**: Compares file hashes to detect:
   - **New articles**: Not in previous state
   - **Updated articles**: Hash changed from previous state
   - **Unchanged articles**: Hash matches previous state

Only new and updated articles are uploaded to the Vector Store.

### State Persistence

- **`state.json`**: Maps filename → SHA-256 hash
- Updated after each successful run
- Enables incremental updates without re-uploading unchanged files

### Vector Store Management

- **First Run**: Creates a new Vector Store and saves ID to `vector_store_id.txt`
- **Subsequent Runs**: Adds delta files to existing Vector Store

## Local Testing

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key
export OPENAI_API_KEY='your-api-key-here'
```

### Run the Job

```bash
python main.py
```

### Expected Output

```
======================================================================
OptiSigns OptiBot - Daily Scraping Job
======================================================================

[1/5] Validating OpenAI API key...
✓ API key validated

[2/5] Loading previous state...
✓ Loaded state for 0 previous article(s)

[3/5] Scraping support articles...
🚀 Starting scraper to fetch at least 35 articles...
📁 Saving to: /path/to/articles
...
✓ Scraping completed

[4/5] Detecting changes...
  📊 Change Summary:
     • New articles:       35
     • Updated articles:   0
     • Unchanged articles: 0

[5/5] Processing delta upload...
📤 Uploading 35 file(s) to OpenAI...
  ✓ article-1.md (ID: file-xxx)
  ...
🆕 Creating new Vector Store...
✓ Created Vector Store: vs_xxxxxxxxxxxxx
💾 State saved to state.json

======================================================================
📊 Job Completion Summary
======================================================================
Articles added:     35
Articles updated:   0
Articles skipped:   0
======================================================================
✅ Job completed successfully!
```

## Docker Deployment

### Build the Image

```bash
cd scraper
docker build -t optisigns-optibot:latest .
```

### Run the Container

```bash
docker run --rm \
  -e OPENAI_API_KEY='your-api-key-here' \
  optisigns-optibot:latest
```

The container runs `main.py` by default and exits cleanly after completion.

## DigitalOcean App Platform (Optional)

The application can be deployed as a scheduled job on DigitalOcean App Platform.

### Configuration Steps

1. **Create a Job Component** (not a Web Service):
   - Component Type: Job
   - Build via Dockerfile
   - Set environment variable `OPENAI_API_KEY`

2. **Configure Schedule**:
   - Cron expression: `0 2 * * *` (daily at 2 AM UTC)
   - Recommended instance: `basic-xxs`

3. **State Persistence**:
   - For production use, configure persistent storage for `state.json` and `vector_store_id.txt`
   - Without persistence, each run treats all articles as new

### Example Configuration

```yaml
jobs:
  - name: daily-scraper
    dockerfile_path: scraper/Dockerfile
    instance_size_slug: basic-xxs
    envs:
      - key: OPENAI_API_KEY
        scope: RUN_TIME
        type: SECRET
```

**Note:** The exact YAML structure may vary based on DigitalOcean's current App Spec format. Refer to their documentation for the latest syntax.

## Monitoring and Logs

### Exit Codes

The job exits with:
- `0`: Success
- `1`: Error occurred

### Log Indicators

**Success:**
```
✅ Job completed successfully!
```

**Errors:**
```
❌ Job failed with error: ...
```

## Troubleshooting

### Issue: "OPENAI_API_KEY not set"

**Solution:** Ensure the environment variable is set:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

### Issue: "No Markdown files found"

**Solution:** The scraper didn't complete. Check:
1. Network connectivity to `support.optisigns.com`
2. Zendesk API availability
3. `articles/` directory permissions

### Issue: State file corruption

**Solution:** Delete `state.json` to reset:
```bash
rm state.json
# Next run will treat all articles as new
```

## Implementation Notes

- **Validation**: Job tested locally using Docker
- **Exit Behavior**: Container exits cleanly after completion
- **State Files**: Contain only filenames and SHA-256 hashes (no article content)
- **API Keys**: Loaded from environment variables only
- **Execution Time**: Typically completes in < 5 minutes

## Next Steps (Optional)

If deploying to production:

1. Set up DigitalOcean App Platform job component
2. Configure environment variables securely
3. Enable persistent storage for state files
4. Set up monitoring and error notifications
5. Test manually before enabling schedule

