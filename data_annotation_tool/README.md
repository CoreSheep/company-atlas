# Data Annotation Tool

A modern, web-based tool for CSV data collection, editing, and annotation with direct S3 upload capabilities.

## Features

- 📤 **CSV File Upload**: Drag-and-drop or click to upload CSV files
- ✏️ **In-Browser Editing**: Edit CSV data in a user-friendly table interface
- 💾 **Local Save**: Download edited CSV files
- ☁️ **S3 Integration**: Upload directly to AWS S3 with configurable credentials
- 🎨 **Elegant UI**: Modern, responsive interface built with React and Tailwind CSS
- 🐳 **Docker Support**: Containerized for easy deployment
- ☁️ **AWS ECS Ready**: Pre-configured for AWS ECS deployment

## Tech Stack

### Backend
- **Django 4.2** - Python web framework
- **Django REST Framework** - RESTful API
- **Boto3** - AWS S3 integration
- **Gunicorn** - WSGI HTTP server

### Frontend
- **React 18** - UI library
- **TypeScript** - Type-safe JavaScript
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Axios** - HTTP client
- **React Hot Toast** - Notifications

### Infrastructure
- **Docker** - Containerization
- **Nginx** - Reverse proxy and static file server
- **AWS ECS** - Container orchestration
- **AWS ECR** - Container registry

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose (for containerized deployment)
- AWS CLI (for ECS deployment)

### Local Development

#### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The backend will be available at `http://localhost:8000`

#### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Docker Deployment

```bash
cd docker
docker-compose up --build
```

This will start both backend and frontend services:
- Frontend: `http://localhost`
- Backend API: `http://localhost/api`

## AWS ECS Deployment

### Prerequisites

1. AWS CLI configured with appropriate credentials
2. ECS cluster created
3. Application Load Balancer configured
4. Security groups configured
5. IAM roles for ECS tasks

### Deployment Steps

1. **Update Configuration**

   Edit `deployment/ecs-task-definition.json`:
   - Replace `YOUR_ACCOUNT_ID` with your AWS account ID
   - Replace `YOUR_ECR_REPO_URL` with your ECR repository URL
   - Update secrets ARNs in AWS Secrets Manager
   - Update subnet and security group IDs

2. **Run Deployment Script**

   ```bash
   chmod +x deployment/deploy.sh
   ./deployment/deploy.sh
   ```

   The script will:
   - Build Docker images
   - Push to ECR
   - Register new task definition
   - Update ECS service

3. **Monitor Deployment**

   ```bash
   aws ecs describe-services \
     --cluster data-annotation-cluster \
     --services data-annotation-service \
     --region us-east-1
   ```

## Environment Variables

### Backend

```env
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
```

### Frontend

```env
VITE_API_URL=http://localhost:8000/api
```

## API Endpoints

### CSV Operations

- `POST /api/files/upload/` - Upload CSV file
- `POST /api/files/save/` - Save edited CSV
- `POST /api/files/upload_to_s3/` - Upload CSV to S3

### S3 Configuration

- `POST /api/s3-config/test_connection/` - Test S3 connection

## Project Structure

```
data_annotation_tool/
├── backend/                 # Django backend
│   ├── data_annotation/    # Django project settings
│   ├── api/               # API views and URLs
│   ├── manage.py
│   └── requirements.txt
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── api/           # API client
│   │   └── types.ts       # TypeScript types
│   ├── package.json
│   └── vite.config.ts
├── docker/                 # Docker configurations
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── nginx.conf
│   └── docker-compose.yml
└── deployment/             # AWS ECS deployment files
    ├── ecs-task-definition.json
    ├── ecs-service-definition.json
    └── deploy.sh
```

## Security Considerations

1. **Secrets Management**: Use AWS Secrets Manager for production credentials
2. **HTTPS**: Always use HTTPS in production
3. **CORS**: Configure CORS appropriately for your domain
4. **File Size Limits**: Adjust `FILE_UPLOAD_MAX_MEMORY_SIZE` as needed
5. **AWS Credentials**: Never commit AWS credentials to version control

## Troubleshooting

### Backend Issues

- Check Django logs: `python manage.py runserver --verbosity 2`
- Verify database migrations: `python manage.py showmigrations
- Test API endpoints with curl or Postman

### Frontend Issues

- Clear browser cache
- Check browser console for errors
- Verify API URL in `.env` file
- Check network tab for API requests

### Docker Issues

- Check container logs: `docker-compose logs`
- Verify port conflicts
- Ensure Docker has enough resources

### ECS Deployment Issues

- Check CloudWatch logs
- Verify task definition JSON syntax
- Check IAM permissions
- Verify security group rules

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is part of the Company Atlas project.

## Support

For issues and questions, please open an issue in the repository.

