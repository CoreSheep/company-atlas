# Fixing Snowflake MFA Issue for Programmatic Access

## Problem
Error: "Multi-factor authentication is required for this account. Log in to Snowsight to enroll."

This means your Snowflake account has MFA enforced at the account level, which prevents programmatic access using password authentication.

## Solutions

### Option 1: Use Key-Pair Authentication (Recommended)
Use RSA key-pair authentication instead of passwords. This bypasses MFA requirements.

1. Generate RSA key pair:
   ```bash
   openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
   openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
   ```

2. Add public key to Snowflake user:
   ```sql
   USE ROLE ACCOUNTADMIN;
   ALTER USER DBT_COMPANY_ATLAS SET RSA_PUBLIC_KEY='<public_key_content>';
   ```

3. Update your Python code to use key-pair authentication:
   ```python
   conn = snowflake.connector.connect(
       account=account,
       user=user,
       private_key=private_key,
       warehouse=warehouse,
       database=database,
       schema=schema
   )
   ```

### Option 2: Account-Level Exception (Requires Admin)
If you have ACCOUNTADMIN access, you can set account-level exceptions for service accounts.

1. Check account-level MFA settings:
   ```sql
   USE ROLE ACCOUNTADMIN;
   SHOW PARAMETERS LIKE 'MFA%' IN ACCOUNT;
   ```

2. Contact your Snowflake admin to:
   - Add an exception for service accounts
   - Or disable MFA requirement for specific users used for automation

### Option 3: Use SSO with Service Account
If your organization uses SSO, you can set up a service account that bypasses MFA.

### Option 4: Temporary Workaround
If you need immediate access, you can:
1. Log into Snowsight (web UI) with your regular user account
2. Enroll in MFA (complete the setup)
3. Use OAuth tokens or session-based authentication temporarily

## Current Status
The user `DBT_COMPANY_ATLAS` has been created, but MFA is blocking password-based programmatic access. You need to either:
- Set up key-pair authentication (Option 1 - recommended)
- Request an account-level exception (Option 2 - if you have admin access)

