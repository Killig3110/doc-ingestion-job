# Daily Job Deployment Guide

## Overview

This document explains how to deploy the OptiSigns OptiBot scraper as a daily scheduled job.

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
cd sraper
docker build -t optisigns-optibot:latest .
```

### Run the Container

```bash
docker run --rm \
  -e OPENAI_API_KEY='your-api-key-here' \
  optisigns-optibot:latest
```

### With Persistent State (Recommended)

To persist state between runs, mount a volume:

```bash
docker run --rm \
  -e OPENAI_API_KEY='your-api-key-here' \
  -v $(pwd)/state:/app/state \
  optisigns-optibot:latest
```

Update `main.py` to use `/app/state/state.json` for state persistence.

## DigitalOcean App Platform Deployment

### Configuration

1. **Create a Worker Component** (not Web Service):
   - Type: Worker
   - Build Command: `docker build -t optisigns-optibot .`
   - Run Command: `python main.py`

2. **Set Environment Variables**:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

3. **Configure Scheduled Job**:
   - Schedule: `0 2 * * *` (daily at 2 AM UTC)
   - Timeout: 30 minutes
   - Instance Count: 1

### App Spec YAML Example

```yaml
name: optisigns-optibot
region: nyc

jobs:
  - name: daily-scraper
    dockerfile_path: sraper/Dockerfile
    instance_count: 1
    instance_size_slug: basic-xxs
    kind: POST_DEPLOY
    schedule:
      cron_spec: "0 2 * * *"  # Daily at 2 AM UTC
    envs:
      - key: OPENAI_API_KEY
        scope: RUN_TIME
        type: SECRET
        value: your-api-key-here
```

### Alternative: GitHub Actions

If you prefer CI/CD over App Platform:

```yaml
# .github/workflows/daily-scrape.yml
name: Daily Scraper

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:  # Manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          cd sraper
          pip install -r requirements.txt
      
      - name: Run daily job
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          cd sraper
          python main.py
      
      - name: Commit state
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add sraper/state.json sraper/vector_store_id.txt
          git diff --quiet && git diff --staged --quiet || git commit -m "Update scraper state [skip ci]"
          git push
```

## Monitoring and Logs

### Check Exit Code

The job exits with:
- `0`: Success
- `1`: Error occurred

### Log Analysis

Look for these key indicators:

**Success:**
```
✅ Job completed successfully!
```

**Errors:**
```
❌ Job failed with error: ...
```

### Metrics to Track

- Articles added per run
- Articles updated per run
- Articles skipped per run
- Job execution time
- Error rate

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

### Issue: Vector Store quota exceeded

**Solution:** OpenAI has limits on Vector Store size:
1. Check your OpenAI plan limits
2. Consider archiving old articles
3. Implement cleanup for outdated content

## Best Practices

1. **Monitoring**: Set up alerts for job failures
2. **Backup**: Regularly backup `state.json` and `vector_store_id.txt`
3. **Logging**: Consider shipping logs to a centralized system
4. **Rate Limits**: The scraper includes delays to respect API limits
5. **State Persistence**: Always use persistent storage for state files

## Production Checklist

- [ ] Environment variables configured securely
- [ ] State persistence enabled (volume mount or persistent storage)
- [ ] Monitoring and alerting configured
- [ ] Log aggregation set up
- [ ] Backup strategy for state files
- [ ] Schedule configured (daily at off-peak hours)
- [ ] Error notifications configured
- [ ] Resource limits appropriate for workload

## Cost Optimization

- Use DigitalOcean's smallest instance (`basic-xxs`) - sufficient for this workload
- Job typically completes in < 5 minutes
- Delta uploads minimize OpenAI API costs
- Consider running during off-peak hours

## Security Notes

- API keys are loaded from environment variables (never hardcoded)
- Container runs as non-root user
- No sensitive data persisted in logs
- State files contain only filenames and hashes (no content)

## Next Steps

1. Deploy to DigitalOcean App Platform or GitHub Actions
2. Configure secrets in deployment platform
3. Set up monitoring and alerts
4. Run first job manually to verify setup
5. Monitor initial runs to tune schedule if needed
