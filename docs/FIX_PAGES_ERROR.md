# Fix: "Get Pages site failed" Error

## The Problem
The error `HttpError: Not Found` and `Get Pages site failed` means **GitHub Pages is not enabled** in your repository settings. The `enablement: true` parameter cannot work until Pages is manually enabled first.

## ✅ REQUIRED: Manual Setup (Must Do First)

### Step 1: Go to Repository Settings
1. Open: **https://github.com/CoreSheep/company-atlas**
2. Click **"Settings"** tab (top menu, next to "Insights")

### Step 2: Navigate to Pages
1. In the left sidebar, scroll down to **"Pages"** (under "Code and automation")
2. Click on **"Pages"**

### Step 3: Enable GitHub Pages
1. You'll see a section titled **"Build and deployment"**
2. Under **"Source"**, you'll see a dropdown (it might say "None" or be empty)
3. Click the dropdown and select: **"GitHub Actions"**
4. Click **"Save"** button

### Step 4: Verify It's Enabled
After saving, you should see:
- ✅ A message saying "Your site is live at https://CoreSheep.github.io/company-atlas/"
- ✅ The source shows "GitHub Actions"
- ✅ A green checkmark or success indicator

## ⚠️ Important Prerequisites

### Repository Must Be Public
- **Free GitHub accounts can only use Pages on public repositories**
- If your repo is private:
  1. Go to **Settings** → **General** → Scroll to **"Danger Zone"**
  2. Click **"Change repository visibility"**
  3. Select **"Make public"**
  4. Confirm

### Check Account Billing
- If you see "account is locked due to a billing issue":
  1. Go to: **https://github.com/settings/billing**
  2. Verify payment method
  3. Resolve any outstanding issues

## After Enabling Pages

### Option 1: Wait for Auto-Deployment
- The workflow will automatically run on the next push to `main`
- Or it may trigger immediately after enabling Pages

### Option 2: Manually Trigger Workflow
1. Go to: **https://github.com/CoreSheep/company-atlas/actions**
2. Click **"Deploy to GitHub Pages"** workflow
3. Click **"Run workflow"** button (top right)
4. Select branch: **"main"**
5. Click **"Run workflow"**

## Expected Result

After enabling Pages and running the workflow, you should see:
- ✅ All workflow steps complete successfully
- ✅ Site available at: **https://CoreSheep.github.io/company-atlas/**

## Why `enablement: true` Doesn't Work Alone

The `enablement: true` parameter in the workflow can only work if:
- The repository already has Pages enabled (even if not configured)
- You have admin/owner permissions
- The repository meets GitHub's requirements

**For first-time setup, you MUST enable Pages manually in Settings first.**

## Still Having Issues?

1. **Check repository visibility**: Must be public for free accounts
2. **Verify permissions**: You need admin/owner access to the repository
3. **Check billing**: No outstanding billing issues
4. **Wait a few minutes**: Sometimes GitHub needs time to process the change
5. **Try again**: Re-run the workflow after enabling Pages

## Quick Checklist

- [ ] Repository is **public**
- [ ] GitHub Pages is **enabled** in Settings → Pages
- [ ] Source is set to **"GitHub Actions"**
- [ ] No billing issues on account
- [ ] Workflow has been triggered (manually or automatically)

