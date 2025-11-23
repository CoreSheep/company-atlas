# How to Enable GitHub Pages

## Quick Setup Steps

### Step 1: Enable GitHub Pages in Repository Settings

1. **Go to your repository**: https://github.com/CoreSheep/company-atlas
2. **Click on "Settings"** (top menu bar)
3. **Scroll down to "Pages"** in the left sidebar (under "Code and automation")
4. **Under "Source"**, select:
   - **Source**: `GitHub Actions` (NOT "Deploy from a branch")
5. **Click "Save"**

### Step 2: Verify the Workflow

After enabling Pages, the workflow will automatically run on the next push, or you can:

1. Go to the **Actions** tab
2. Find the **"Deploy to GitHub Pages"** workflow
3. Click **"Run workflow"** → **"Run workflow"** button

### Step 3: Wait for Deployment

- Deployment typically takes 1-2 minutes
- You can watch the progress in the **Actions** tab
- Once complete, your site will be available at: **https://CoreSheep.github.io/company-atlas/**

## Troubleshooting

### Error: "Get Pages site failed"
**Solution**: This means GitHub Pages is not enabled. Follow Step 1 above to enable it.

### Error: "Not Found"
**Solution**: 
1. Make sure you selected **"GitHub Actions"** as the source (not a branch)
2. Wait a few minutes after enabling and try again
3. Check that the repository is public (or you have GitHub Pro/Team if private)

### Workflow Not Running
**Solution**:
1. Check that the workflow file exists at `.github/workflows/pages.yml`
2. Verify you're pushing to the `main` branch
3. Check the **Actions** tab for any error messages

### Site Not Accessible
**Solution**:
1. Wait 2-3 minutes after deployment completes
2. Clear your browser cache
3. Try accessing: `https://CoreSheep.github.io/company-atlas/`
4. Check the **Pages** section in Settings to see the published URL

## Visual Guide

After enabling GitHub Actions as the source, you should see:
- ✅ "Your site is live at https://CoreSheep.github.io/company-atlas/"
- The source should show "GitHub Actions" (not a branch name)

## Important Notes

- The first deployment may take longer (2-3 minutes)
- Subsequent deployments are usually faster (1-2 minutes)
- The site URL is based on your username: `https://[username].github.io/[repository-name]/`
- If you change the repository name, the URL will change

