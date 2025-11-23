# How to Reset Snowflake Password

## Method 1: Using Snowflake Web UI

1. Go to https://app.snowflake.com/
2. Click "Forgot Password?" on the login page
3. Enter your username or email
4. Follow the password reset instructions sent to your email

## Method 2: Using SQL (if you have Admin Access)

If you have access as ACCOUNTADMIN or another admin user:

```sql
-- Reset password for your user
ALTER USER LI37118 SET PASSWORD = 'YourNewPassword123';

-- Or if you want to force password change on next login
ALTER USER LI37118 SET PASSWORD = 'YourNewPassword123' MUST_CHANGE_PASSWORD = TRUE;
```

## Method 3: Verify Your User Account Details

If you can connect through the web UI, run these queries to verify your account:

```sql
-- Check your user information
SELECT 
    USER_NAME,
    DISPLAY_NAME,
    EMAIL,
    LOGIN_NAME,
    DEFAULT_WAREHOUSE,
    DISABLED,
    MUST_CHANGE_PASSWORD,
    LAST_SUCCESS_LOGIN
FROM TABLE(INFORMATION_SCHEMA.USERS())
WHERE USER_NAME = 'LI37118';

-- Check if account is locked or disabled
SELECT 
    USER_NAME,
    DISABLED,
    LOCKED_UNTIL_TIME,
    MUST_CHANGE_PASSWORD,
    LAST_SUCCESS_LOGIN
FROM TABLE(INFORMATION_SCHEMA.USERS())
WHERE USER_NAME = 'LI37118';

-- Verify your login name format (might be different from username)
SELECT 
    USER_NAME,
    LOGIN_NAME
FROM TABLE(INFORMATION_SCHEMA.USERS())
WHERE USER_NAME = 'LI37118';
```

## Common Issues

1. **Username vs Login Name**: Your LOGIN_NAME might be different from USER_NAME
   - Check the LOGIN_NAME column in the queries above
   - You might need to use LOGIN_NAME instead of USER_NAME in credentials

2. **Account is Disabled**: If DISABLED = TRUE, contact your Snowflake admin

3. **Account is Locked**: If LOCKED_UNTIL_TIME is set, wait until that time or contact admin

4. **Password Expired**: If MUST_CHANGE_PASSWORD = TRUE, you need to reset password

5. **Account Format**: Try different account formats:
   - Full: `NRKZBJU-LI37118`
   - Short: `NRKZBJU` (organization name)
   - Just account: `LI37118`

## Update Your .env File

After resetting password, update your `~/.env` file:

```bash
SNOWFLAKE_ACCOUNT=NRKZBJU-LI37118
SNOWFLAKE_USER=LI37118
SNOWFLAKE_PASSWORD=YourNewPassword123
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=COMPANY_ATLAS
SNOWFLAKE_SCHEMA=RAW
```

Make sure:
- No quotes around the password (unless it has special characters)
- No spaces around the `=`
- No trailing spaces

