# GitHub Pages Setup Guide

## Overview
The Company Atlas website is configured to deploy automatically to GitHub Pages when changes are pushed to the `main` branch.

## Repository URL
- **Repository**: `CoreSheep/company-atlas`
- **GitHub Pages URL**: `https://CoreSheep.github.io/company-atlas/`

## Setup Steps

### 1. Enable GitHub Pages in Repository Settings

1. Go to your repository on GitHub: `https://github.com/CoreSheep/company-atlas`
2. Click on **Settings** (top menu)
3. Scroll down to **Pages** in the left sidebar
4. Under **Source**, select:
   - **Source**: `GitHub Actions`
5. Save the settings

### 2. Verify Workflow File

The GitHub Actions workflow is located at:
- `.github/workflows/pages.yml`

This workflow:
- Triggers on pushes to `main` branch
- Deploys the `website/` directory to GitHub Pages
- Uses the latest GitHub Actions for Pages deployment

### 3. Update Data Files

Before deploying, ensure data files are up to date:

```bash
# Download latest data from Snowflake
python pipelines/marts/download_unified_companies.py

# Copy data files to website directory
cp data/marts/*.json website/data/marts/
```

### 4. Deploy

The deployment happens automatically when you push to `main`. You can also trigger manually:

1. Go to **Actions** tab in GitHub
2. Select **Deploy to GitHub Pages** workflow
3. Click **Run workflow**

### 5. Access Your Site

After deployment (usually takes 1-2 minutes), your site will be available at:
- `https://CoreSheep.github.io/company-atlas/`

## Troubleshooting

### Workflow Not Running
- Check that GitHub Pages is enabled in repository settings
- Verify the workflow file is in `.github/workflows/`
- Check the **Actions** tab for any error messages

### Data Not Loading
- Ensure `website/data/marts/` contains `unified_companies.json` and `statistics.json`
- Check browser console for CORS or path errors
- Verify the data path in `website/assets/js/main.js` is correct

### Site Not Updating
- Wait 1-2 minutes after push
- Check the **Actions** tab to see if deployment completed
- Clear browser cache and hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

## Manual Deployment

If you need to update data files manually:

```bash
# 1. Download fresh data
cd /path/to/company-atlas/company-atlas
python pipelines/marts/download_unified_companies.py

# 2. Copy to website directory
cp data/marts/*.json website/data/marts/

# 3. Commit and push
git add website/data/marts/
git commit -m "Update website data files"
git push origin main
```

## Custom Domain (Optional)

To use a custom domain:
1. Add a `CNAME` file in the `website/` directory with your domain
2. Configure DNS records as per GitHub Pages documentation
3. Update repository settings to use custom domain

