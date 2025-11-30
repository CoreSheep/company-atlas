# Frontend-Backend Communication Architecture

This document explains how the frontend (React) and backend (Django) communicate and how routing works in different deployment scenarios.

## Overview

The Data Annotation Tool uses a **client-server architecture** where:
- **Frontend**: React SPA (Single Page Application) served by Nginx
- **Backend**: Django REST Framework API
- **Communication**: HTTP/REST API using JSON and multipart/form-data

## Communication Flow

### 1. Development Environment

```
┌─────────────────┐         ┌──────────────────┐
│   React App     │         │  Django Backend  │
│  (Port 3000)    │────────▶│   (Port 8000)    │
│                 │         │                  │
│  Vite Dev       │         │  Gunicorn/       │
│  Server         │         │  runserver       │
└─────────────────┘         └──────────────────┘
         │                           │
         │                           │
         └─────────── HTTP ──────────┘
```

**How it works:**
1. Frontend runs on `http://localhost:3000` (Vite dev server)
2. Backend runs on `http://localhost:8000` (Django)
3. Vite proxy forwards `/api/*` requests to backend

**Configuration:**

```typescript:frontend/vite.config.ts
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',  // Proxy to Django
      changeOrigin: true,
    },
  },
}
```

**API Client Configuration:**

```typescript:frontend/src/api/client.ts
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,  // Base URL for all API calls
  headers: {
    'Content-Type': 'application/json',
  },
})
```

### 2. Production Environment (Docker)

```
┌─────────────────────────────────────────────────┐
│              User Browser                       │
│         (http://yourdomain.com)                 │
└──────────────────┬──────────────────────────────┘
                   │
                   │ HTTP Request
                   ▼
┌─────────────────────────────────────────────────┐
│            Nginx Container                      │
│            (Port 80)                            │
│  ┌──────────────────────────────────────────┐  │
│  │  Static Files (React Build)              │  │
│  │  - index.html                            │  │
│  │  - CSS, JS bundles                       │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  API Proxy                               │  │
│  │  location /api → backend:8000           │  │
│  └──────────────────────────────────────────┘  │
└───────────────┬─────────────────────────────────┘
                │
                │ Proxy Pass
                │ (localhost:8000)
                ▼
┌─────────────────────────────────────────────────┐
│         Django Backend Container                │
│         (Port 8000)                             │
│  ┌──────────────────────────────────────────┐  │
│  │  Django REST Framework                   │  │
│  │  - /api/files/upload/                    │  │
│  │  - /api/files/save/                      │  │
│  │  - /api/files/upload_to_s3/              │  │
│  │  - /api/s3-config/test_connection/       │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**Nginx Configuration:**

```nginx:docker/nginx.conf
server {
    listen 80;
    
    # Serve React static files
    location / {
        try_files $uri $uri/ /index.html;  # SPA routing
    }
    
    # Proxy API requests to backend
    location /api {
        proxy_pass http://127.0.0.1:8000;  # Backend container
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_added_x_forwarded_for;
    }
}
```

**Note:** In Docker Compose, containers share a network, so `127.0.0.1:8000` refers to the backend container.

### 3. AWS ECS Deployment

```
┌─────────────────────────────────────────────────┐
│         AWS Application Load Balancer            │
│         (ALB - Port 80/443)                     │
└──────────────────┬───────────────────────────────┘
                   │
                   │ HTTP/HTTPS
                   ▼
┌─────────────────────────────────────────────────┐
│              ECS Task                           │
│  ┌──────────────────────────────────────────┐  │
│  │  Nginx Container (Frontend)               │  │
│  │  - Serves React static files             │  │
│  │  - Proxies /api to backend               │  │
│  └──────────────┬─────────────────────────────┘  │
│                 │                                 │
│                 │ localhost:8000                  │
│                 ▼                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Django Container (Backend)              │  │
│  │  - Gunicorn on port 8000                │  │
│  │  - Django REST Framework                 │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Request Flow Examples

### Example 1: Upload CSV File

**Frontend Request:**
```typescript
// frontend/src/components/FileUpload.tsx
const formData = new FormData()
formData.append('file', file)

const response = await apiClient.post('/files/upload/', formData, {
  headers: {
    'Content-Type': 'multipart/form-data',
  },
})
```

**Request Path:**
```
Browser → Nginx (/) → React App
User clicks upload → apiClient.post('/files/upload/', ...)
  → Nginx (/api/files/upload/) → Backend (http://127.0.0.1:8000/api/files/upload/)
```

**Backend Routing:**
```python
# backend/data_annotation/urls.py
urlpatterns = [
    path('api/', include('api.urls')),  # Routes /api/* to api app
]

# backend/api/urls.py
router.register(r'files', CSVFileViewSet, basename='csvfile')
# Creates: /api/files/upload/ (POST)
```

**Backend Handler:**
```python
# backend/api/views.py
class CSVFileViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def upload(self, request):
        # Handle file upload
        return Response({...})
```

### Example 2: Save CSV Data

**Frontend Request:**
```typescript
// frontend/src/components/CSVEditor.tsx
const response = await apiClient.post('/files/save/', {
  filename: editedData.filename,
  headers: editedData.headers,
  rows: editedData.rows,
}, {
  responseType: 'blob',  // Download as file
})
```

**Request Path:**
```
Browser → Nginx → React App
apiClient.post('/files/save/', {...})
  → Nginx (/api/files/save/) → Backend (/api/files/save/)
```

**Backend Response:**
```python
# backend/api/views.py
@action(detail=False, methods=['post'])
def save(self, request):
    # Generate CSV
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
```

### Example 3: Upload to S3

**Frontend Request:**
```typescript
// frontend/src/components/S3Config.tsx
const response = await apiClient.post('/files/upload_to_s3/', {
  ...config,  // AWS credentials, bucket, region
  filename: csvData.filename,
  headers: csvData.headers,
  rows: csvData.rows,
  s3_key: s3Key,
})
```

**Request Path:**
```
Browser → Nginx → React App
apiClient.post('/files/upload_to_s3/', {...})
  → Nginx (/api/files/upload_to_s3/) → Backend (/api/files/upload_to_s3/)
  → Backend uploads to AWS S3 → Returns S3 URL
```

## URL Routing Details

### Frontend Routes (React Router - if used)

The frontend is a Single Page Application (SPA), so all routes are handled client-side:

```
/                    → FileUpload component
/editor              → CSVEditor component (when file loaded)
```

**Nginx SPA Configuration:**
```nginx
location / {
    try_files $uri $uri/ /index.html;  # Always serve index.html for SPA
}
```

### Backend Routes (Django)

**Root URLs (`data_annotation/urls.py`):**
```
/                    → dashboard view (HTML)
/api/health/         → health_check view (JSON)
/admin/              → Django admin
/api/                → Include api.urls
```

**API URLs (`api/urls.py`):**
```
/api/files/upload/              → CSVFileViewSet.upload (POST)
/api/files/save/                → CSVFileViewSet.save (POST)
/api/files/upload_to_s3/        → CSVFileViewSet.upload_to_s3 (POST)
/api/s3-config/test_connection/ → S3ConfigViewSet.test_connection (POST)
```

**Django REST Framework Router:**
- `router.register(r'files', CSVFileViewSet)` creates:
  - `/api/files/upload/` (custom action)
  - `/api/files/save/` (custom action)
  - `/api/files/upload_to_s3/` (custom action)

## CORS Configuration

**Backend CORS Settings:**
```python
# backend/data_annotation/settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True
```

**Why CORS is needed:**
- In development, frontend (port 3000) and backend (port 8000) are different origins
- Browser enforces CORS policy for cross-origin requests
- In production (same origin via Nginx), CORS is less critical but still configured

## Environment Variables

### Frontend
```bash
# .env or environment
VITE_API_URL=http://localhost:8000/api  # Development
# In production, use relative URLs or set to production API URL
```

### Backend
```bash
# .env or environment
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

## Data Flow Summary

1. **User Action** → Frontend component (React)
2. **API Call** → `apiClient.post/get()` (Axios)
3. **HTTP Request** → Nginx (production) or Vite proxy (development)
4. **Proxy/Routing** → Backend Django server
5. **URL Routing** → Django URL patterns → ViewSet action
6. **Processing** → Django view processes request
7. **Response** → JSON or file download
8. **Frontend Update** → React component updates state

## Key Technologies

- **Frontend HTTP Client**: Axios
- **Backend Framework**: Django REST Framework
- **Routing**: 
  - Frontend: React Router (if used) + Nginx SPA routing
  - Backend: Django URL routing + DRF Router
- **Proxy**: Nginx (production) or Vite (development)
- **CORS**: django-cors-headers

## Troubleshooting

### Issue: CORS errors in development
**Solution:** Check `CORS_ALLOWED_ORIGINS` in `settings.py` includes your frontend URL

### Issue: 404 on API routes
**Solution:** 
- Check Nginx proxy configuration
- Verify Django URL patterns
- Check API base URL in frontend

### Issue: API calls fail in production
**Solution:**
- Verify Nginx proxy_pass URL
- Check backend container is running
- Verify network connectivity between containers

### Issue: Static files not loading
**Solution:**
- Check Nginx root directory
- Verify React build output
- Check file permissions

## Security Considerations

1. **CORS**: Configured to allow only specific origins
2. **CSRF**: Django CSRF protection enabled
3. **Authentication**: Optional (configurable via `REQUIRE_AUTH`)
4. **HTTPS**: Use HTTPS in production (configure ALB/nginx)
5. **Headers**: Security headers configured in Nginx and Django

## Summary

The communication architecture uses:
- **REST API** for data exchange
- **Nginx reverse proxy** in production
- **Vite dev proxy** in development
- **Django URL routing** for backend endpoints
- **Axios** for HTTP requests from frontend
- **JSON** for most data, **multipart/form-data** for file uploads

This architecture provides:
- ✅ Separation of concerns (frontend/backend)
- ✅ Scalability (can scale frontend/backend independently)
- ✅ Security (CORS, CSRF, authentication)
- ✅ Flexibility (easy to add new endpoints)

