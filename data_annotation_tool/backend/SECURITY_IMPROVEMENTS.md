# Security Improvements Documentation

This document outlines the security enhancements made to the Data Annotation Tool backend.

## Overview

The backend has been enhanced with comprehensive security measures including authentication, input validation, file validation, credential management, and security headers.

## Security Features Implemented

### 1. Authentication & Authorization

**Configuration:**
- Authentication is **optional** and controlled by the `REQUIRE_AUTH` environment variable
- Default: `REQUIRE_AUTH=False` (authentication disabled for development)
- Set `REQUIRE_AUTH=True` in production to enable authentication

**Implementation:**
- Django REST Framework authentication (Session and Basic Auth)
- ViewSets require authentication when `REQUIRE_AUTH=True`
- Health check endpoint remains public (no authentication required)

**Usage:**
```bash
# Enable authentication in production
export REQUIRE_AUTH=True
```

### 2. File Validation

**Enhanced CSV Validation:**
- ✅ File extension validation (`.csv` only)
- ✅ File size validation (max 10MB)
- ✅ **Content validation** - validates actual CSV format, not just extension
- ✅ Header validation (non-empty headers required)
- ✅ Column count limit (max 100 columns)
- ✅ Row count limit (max 100,000 rows)
- ✅ Encoding validation (UTF-8)

**Functions:**
- `validate_csv_content()` - Validates CSV structure and content
- `sanitize_filename()` - Prevents path traversal and sanitizes filenames

### 3. Input Validation & Sanitization

**Filename Sanitization:**
- Removes path components (prevents directory traversal)
- Removes special characters (keeps only alphanumeric, dots, hyphens, underscores)
- Limits filename length (max 255 characters)
- Ensures `.csv` extension

**S3 Key Validation:**
- Prevents path traversal (`..` not allowed)
- Prevents absolute paths (no leading `/`)
- Validates bucket name format (AWS S3 naming rules)
- Sanitizes S3 keys

**Data Validation:**
- Validates data types (headers and rows must be arrays)
- Validates array lengths (prevents DoS attacks)
- Validates required fields

### 4. AWS Credentials Management

**Secure Credential Handling:**
- ✅ **Environment variables first** - Uses `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` from environment
- ✅ **Request body fallback** - Falls back to request body if environment variables not set
- ✅ **No credential logging** - Credentials are never logged or exposed in error messages

**Function:**
- `get_aws_credentials()` - Safely retrieves credentials with environment variable priority

**Best Practice:**
```bash
# Set in environment variables (recommended)
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

### 5. Security Headers

**HTTP Security Headers:**
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-XSS-Protection` - Browser XSS filter
- `Strict-Transport-Security` - HSTS (only in production)
- `Content-Security-Policy` - Ready for implementation

**Cookie Security:**
- `CSRF_COOKIE_SECURE` - HTTPS only in production
- `CSRF_COOKIE_HTTPONLY` - Prevents JavaScript access
- `SESSION_COOKIE_SECURE` - HTTPS only in production
- `SESSION_COOKIE_HTTPONLY` - Prevents JavaScript access
- `SESSION_COOKIE_SAMESITE` - CSRF protection

### 6. Rate Limiting

**Throttling:**
- Anonymous users: 100 requests/hour
- Authenticated users: 1000 requests/hour
- Applied to all API endpoints

### 7. Error Handling

**Improved Error Messages:**
- Specific error codes (400, 401, 403, 404, 500)
- Detailed error messages for debugging
- No sensitive information in error responses
- Proper exception handling for AWS errors

**Error Types Handled:**
- `NoCredentialsError` - AWS credentials missing/invalid
- `ClientError` - AWS S3 client errors (with specific error codes)
- `UnicodeDecodeError` - File encoding errors
- `csv.Error` - CSV parsing errors
- Generic exceptions with safe error messages

### 8. S3 Upload Security

**Enhanced S3 Upload:**
- Server-side encryption enabled (`AES256`)
- Proper content type headers (`text/csv; charset=utf-8`)
- UTF-8 encoding for file content
- Path traversal prevention in S3 keys

## Configuration

### Environment Variables

```bash
# Authentication (optional)
REQUIRE_AUTH=True  # Enable authentication (default: False)

# AWS Credentials (recommended)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_STORAGE_BUCKET_NAME=your_bucket
AWS_S3_REGION_NAME=us-east-1

# Security
SECRET_KEY=your-secret-key  # Required in production
DEBUG=False  # Disable in production
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
```

### Settings Configuration

All security settings are in `data_annotation/settings.py`:

- `REST_FRAMEWORK` - Authentication and permissions
- `SECURE_BROWSER_XSS_FILTER` - XSS protection
- `SECURE_CONTENT_TYPE_NOSNIFF` - MIME sniffing protection
- `X_FRAME_OPTIONS` - Clickjacking protection
- `SECURE_HSTS_SECONDS` - HSTS configuration
- `CSRF_COOKIE_SECURE` - CSRF cookie security
- `SESSION_COOKIE_SECURE` - Session cookie security

## Migration Guide

### For Development (No Authentication)

No changes required. The backend works as before with authentication disabled by default.

### For Production (With Authentication)

1. **Set environment variables:**
   ```bash
   export REQUIRE_AUTH=True
   export SECRET_KEY=your-secret-key
   export DEBUG=False
   export ALLOWED_HOSTS=yourdomain.com
   ```

2. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

3. **Update frontend** (if needed):
   - Add authentication headers to API requests
   - Implement login/logout functionality
   - Handle 401/403 errors

### Frontend Integration

If authentication is enabled, update the frontend API client:

```typescript
// frontend/src/api/client.ts
import axios from 'axios'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // For session authentication
})

// Add request interceptor for token-based auth (if using tokens)
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

## Security Checklist

- [x] Authentication and authorization
- [x] Input validation and sanitization
- [x] File content validation (not just extension)
- [x] Path traversal prevention
- [x] Credential management (environment variables)
- [x] Security headers
- [x] Rate limiting
- [x] Error handling (no sensitive data exposure)
- [x] S3 encryption
- [x] CSRF protection
- [x] XSS protection
- [x] Clickjacking protection

## Testing Security

### Test File Validation

```bash
# Test with invalid file
curl -X POST http://localhost:8000/api/files/upload/ \
  -F "file=@not_a_csv.txt"

# Test with oversized file
curl -X POST http://localhost:8000/api/files/upload/ \
  -F "file=@large_file.csv"
```

### Test Input Validation

```bash
# Test with path traversal
curl -X POST http://localhost:8000/api/files/upload_to_s3/ \
  -H "Content-Type: application/json" \
  -d '{"s3_key": "../../etc/passwd", ...}'
```

### Test Authentication

```bash
# Test without authentication (should fail if REQUIRE_AUTH=True)
curl -X POST http://localhost:8000/api/files/upload/ \
  -F "file=@test.csv"
```

## Recommendations

1. **Always use environment variables** for AWS credentials in production
2. **Enable authentication** (`REQUIRE_AUTH=True`) in production
3. **Use HTTPS** in production (required for secure cookies)
4. **Set strong SECRET_KEY** in production
5. **Disable DEBUG** in production
6. **Configure ALLOWED_HOSTS** properly
7. **Use AWS IAM roles** instead of access keys when possible (e.g., on ECS)
8. **Monitor rate limits** and adjust if needed
9. **Regular security audits** of dependencies
10. **Keep Django and dependencies updated**

## Additional Security Measures (Future)

- [ ] JWT token authentication
- [ ] API key authentication
- [ ] Request signing
- [ ] Audit logging
- [ ] IP whitelisting
- [ ] Content Security Policy (CSP)
- [ ] File virus scanning
- [ ] Request size limits per endpoint
- [ ] Database query optimization (prevent DoS)
- [ ] Two-factor authentication

## Support

For security issues or questions, please review:
- Django Security: https://docs.djangoproject.com/en/stable/topics/security/
- DRF Security: https://www.django-rest-framework.org/api-guide/authentication/
- AWS Security Best Practices: https://docs.aws.amazon.com/security/

