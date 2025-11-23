# GitHub Pages Troubleshooting Guide

## Current Issue: "Get Pages site failed"

### Solution 1: Enable Pages Manually (Recommended First Step)

Even with `enablement: true`, you may need to enable Pages manually first:

1. Go to: **https://github.com/CoreSheep/company-atlas/settings/pages**
2. Under **"Source"**, select: **"GitHub Actions"**
3. Click **"Save"**

### Solution 2: Verify Repository Visibility

**GitHub Pages on free accounts only works with public repositories.**

1. Go to: **https://github.com/CoreSheep/company-atlas/settings**
2. Scroll to **"Danger Zone"** at the bottom
3. If repository is private:
   - Click **"Change repository visibility"**
   - Select **"Make public"**
   - Confirm the change

### Solution 3: Check GitHub Actions Permissions

1. Go to: **https://github.com/CoreSheep/company-atlas/settings/actions**
2. Under **"Workflow permissions"**:
   - Select **"Read and write permissions"**
   - Check **"Allow GitHub Actions to create and approve pull requests"**
3. Click **"Save"**

### Solution 4: Verify Environment Settings

1. Go to: **https://github.com/CoreSheep/company-atlas/settings/environments**
2. If you see **"github-pages"** environment:
   - Click on it
   - Under **"Deployment branches"**, ensure your branch is allowed
   - Or set to **"All branches"**

### Solution 5: Check Account Billing Status

If you see "account is locked due to a billing issue":

1. Go to: **https://github.com/settings/billing**
2. Verify your payment method is valid
3. Check for any outstanding invoices
4. For free accounts, ensure you haven't exceeded usage limits

### Solution 6: Manual Workflow Trigger

After making the above changes:

1. Go to: **https://github.com/CoreSheep/company-atlas/actions**
2. Select **"Deploy to GitHub Pages"** workflow
3. Click **"Run workflow"** → **"Run workflow"**

## Quick Checklist

- [ ] Repository is **public** (required for free accounts)
- [ ] GitHub Pages is enabled with **"GitHub Actions"** as source
- [ ] GitHub Actions has **read and write** permissions
- [ ] No billing issues on your GitHub account
- [ ] Workflow file exists at `.github/workflows/pages.yml`

## Expected Workflow Steps

When working correctly, you should see:
1. ✅ Checkout
2. ✅ Setup Pages (with enablement)
3. ✅ Upload artifact
4. ✅ Deploy to GitHub Pages

## After Successful Deployment

Your site will be available at:
**https://CoreSheep.github.io/company-atlas/**

Deployment typically takes 1-2 minutes after the workflow completes.

