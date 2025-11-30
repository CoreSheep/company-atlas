import csv
import io
import json
import boto3
import re
from botocore.exceptions import ClientError, NoCredentialsError
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.core.exceptions import ValidationError
from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django.conf import settings
import os
from datetime import datetime


def validate_csv_content(file_content):
    """
    Validate that the file content is actually CSV format.
    Returns (is_valid, error_message)
    """
    try:
        # Try to parse as CSV
        csv_reader = csv.reader(io.StringIO(file_content))
        rows = list(csv_reader)
        
        if len(rows) == 0:
            return False, "CSV file is empty"
        
        # Check if first row looks like headers (non-empty)
        if len(rows[0]) == 0 or all(not cell.strip() for cell in rows[0]):
            return False, "CSV file has invalid headers"
        
        # Check for reasonable number of columns (not too many)
        num_columns = len(rows[0])
        if num_columns > 100:
            return False, "CSV file has too many columns (max 100)"
        
        # Check for reasonable row count (not too many)
        if len(rows) > 100000:
            return False, "CSV file has too many rows (max 100,000)"
        
        return True, None
    except csv.Error as e:
        return False, f"Invalid CSV format: {str(e)}"
    except Exception as e:
        return False, f"Error validating CSV: {str(e)}"


def sanitize_filename(filename):
    """Sanitize filename to prevent directory traversal and other attacks."""
    # Remove path components
    filename = os.path.basename(filename)
    # Remove any non-alphanumeric characters except dots, hyphens, and underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    return filename


def get_aws_credentials(request_data):
    """
    Get AWS credentials from environment variables first, then fall back to request data.
    Returns (access_key, secret_key) or (None, None) if not available.
    """
    # Try environment variables first (more secure)
    access_key = settings.AWS_ACCESS_KEY_ID or request_data.get('aws_access_key_id')
    secret_key = settings.AWS_SECRET_ACCESS_KEY or request_data.get('aws_secret_access_key')
    
    return access_key, secret_key


@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint that returns JSON."""
    return JsonResponse({
        'status': 'API is running',
        'message': 'Welcome to the Data Annotation Tool API!',
        'endpoints': {
            '/api/files/upload/': 'POST - Upload a CSV file',
            '/api/files/save/': 'POST - Save edited CSV data locally',
            '/api/files/upload_to_s3/': 'POST - Upload edited CSV data to S3',
            '/api/s3-config/test_connection/': 'POST - Test AWS S3 connection',
            '/admin/': 'Django Admin Panel',
        }
    })


def dashboard(request):
    """Simple dashboard view for backend."""
    endpoints = [
        {
            'path': '/api/files/upload/',
            'method': 'POST',
            'description': 'Upload a CSV file and get its contents parsed',
            'example': {
                'method': 'POST',
                'url': '/api/files/upload/',
                'body': 'multipart/form-data with "file" field containing CSV file'
            }
        },
        {
            'path': '/api/files/save/',
            'method': 'POST',
            'description': 'Save edited CSV data and download as file',
            'example': {
                'method': 'POST',
                'url': '/api/files/save/',
                'body': '{"filename": "data.csv", "headers": ["col1", "col2"], "rows": [{"col1": "val1", "col2": "val2"}]}'
            }
        },
        {
            'path': '/api/files/upload_to_s3/',
            'method': 'POST',
            'description': 'Upload edited CSV data directly to AWS S3',
            'example': {
                'method': 'POST',
                'url': '/api/files/upload_to_s3/',
                'body': '{"aws_access_key_id": "...", "aws_secret_access_key": "...", "bucket_name": "...", "region_name": "us-east-1", "s3_key": "path/to/file.csv", "filename": "data.csv", "headers": [...], "rows": [...]}'
            }
        },
        {
            'path': '/api/s3-config/test_connection/',
            'method': 'POST',
            'description': 'Test AWS S3 connection with provided credentials',
            'example': {
                'method': 'POST',
                'url': '/api/s3-config/test_connection/',
                'body': '{"aws_access_key_id": "...", "aws_secret_access_key": "...", "bucket_name": "my-bucket", "region_name": "us-east-1"}'
            }
        },
    ]
    
    context = {
        'endpoints': endpoints,
        'api_base_url': request.build_absolute_uri('/api/'),
        'admin_url': request.build_absolute_uri('/admin/'),
    }
    return render(request, 'dashboard/index.html', context)


class CSVFileViewSet(viewsets.ViewSet):
    """
    ViewSet for handling CSV file operations.
    Authentication is configurable via REQUIRE_AUTH environment variable.
    """
    parser_classes = [MultiPartParser, JSONParser]
    # Authentication is optional - controlled by REQUIRE_AUTH setting
    permission_classes = [IsAuthenticated] if getattr(settings, 'REQUIRE_AUTH', False) else [AllowAny]
    throttle_classes = [UserRateThrottle]

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload a CSV file."""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']
        
        # Validate file extension
        if not file.name.lower().endswith('.csv'):
            return Response(
                {'error': 'File must be a CSV file'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 10MB)
        if file.size > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
            return Response(
                {'error': f'File too large. Maximum size is {settings.FILE_UPLOAD_MAX_MEMORY_SIZE / 1024 / 1024}MB'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Read and decode file content
            decoded_file = file.read().decode('utf-8')
            
            # Validate CSV content
            is_valid, error_msg = validate_csv_content(decoded_file)
            if not is_valid:
                return Response(
                    {'error': error_msg}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(decoded_file))
            rows = list(csv_reader)
            
            if not rows:
                return Response(
                    {'error': 'CSV file is empty'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            headers = list(rows[0].keys())
            
            # Sanitize filename
            safe_filename = sanitize_filename(file.name)

            return Response({
                'filename': safe_filename,
                'headers': headers,
                'rows': rows,
                'row_count': len(rows),
            }, status=status.HTTP_200_OK)
        except UnicodeDecodeError:
            return Response(
                {'error': 'File encoding error. Please ensure the file is UTF-8 encoded'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error processing CSV file: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def save(self, request):
        """Save edited CSV data locally."""
        filename = request.data.get('filename', 'edited_data.csv')
        headers = request.data.get('headers', [])
        rows = request.data.get('rows', [])

        # Validate input
        if not isinstance(headers, list) or not isinstance(rows, list):
            return Response(
                {'error': 'Invalid data format. Headers and rows must be arrays'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if not headers:
            return Response(
                {'error': 'No headers provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not rows:
            return Response(
                {'error': 'No data rows provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate header count
        if len(headers) > 100:
            return Response(
                {'error': 'Too many columns (max 100)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate row count
        if len(rows) > 100000:
            return Response(
                {'error': 'Too many rows (max 100,000)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Sanitize filename
        safe_filename = sanitize_filename(filename)
        if not safe_filename.endswith('.csv'):
            safe_filename += '.csv'

        try:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            writer.writerows(rows)

            response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            response['X-Content-Type-Options'] = 'nosniff'
            return response
        except Exception as e:
            return Response(
                {'error': f'Error generating CSV file: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def upload_to_s3(self, request):
        """Upload edited CSV data to S3."""
        # Get credentials (prefer environment variables)
        aws_access_key_id, aws_secret_access_key = get_aws_credentials(request.data)
        
        bucket_name = request.data.get('bucket_name')
        region_name = request.data.get('region_name', settings.AWS_S3_REGION_NAME)
        s3_key = request.data.get('s3_key')
        filename = request.data.get('filename', 'edited_data.csv')
        headers = request.data.get('headers', [])
        rows = request.data.get('rows', [])

        # Validate required fields
        if not aws_access_key_id or not aws_secret_access_key:
            return Response(
                {'error': 'AWS credentials not provided. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in environment variables or request body'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if not bucket_name:
            return Response(
                {'error': 'Bucket name is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not s3_key:
            return Response(
                {'error': 'S3 key (path) is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate bucket name format
        if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', bucket_name.lower()):
            return Response(
                {'error': 'Invalid bucket name format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate S3 key (path)
        if '..' in s3_key or s3_key.startswith('/'):
            return Response(
                {'error': 'Invalid S3 key. Path traversal not allowed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Sanitize S3 key
        s3_key = sanitize_filename(s3_key)
        if not s3_key.endswith('.csv'):
            s3_key += '.csv'

        # Validate data
        if not isinstance(headers, list) or not isinstance(rows, list):
            return Response(
                {'error': 'Invalid data format. Headers and rows must be arrays'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if not headers or not rows:
            return Response(
                {'error': 'No data to upload'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate limits
        if len(headers) > 100:
            return Response(
                {'error': 'Too many columns (max 100)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(rows) > 100000:
            return Response(
                {'error': 'Too many rows (max 100,000)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            writer.writerows(rows)
            csv_content = output.getvalue()

            s3.put_object(
                Bucket=bucket_name, 
                Key=s3_key, 
                Body=csv_content.encode('utf-8'), 
                ContentType='text/csv; charset=utf-8',
                ServerSideEncryption='AES256'  # Enable encryption
            )
            s3_url = f"https://{bucket_name}.s3.{region_name}.amazonaws.com/{s3_key}"

            return Response(
                {'message': 'File uploaded to S3 successfully', 's3_url': s3_url}, 
                status=status.HTTP_200_OK
            )
        except NoCredentialsError:
            return Response(
                {'error': 'AWS credentials not found or invalid'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code == 'AccessDenied':
                return Response(
                    {'error': f'Access denied: {error_message}'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            elif error_code == 'NoSuchBucket':
                return Response(
                    {'error': f'Bucket "{bucket_name}" not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            else:
                return Response(
                    {'error': f'S3 client error: {error_message}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class S3ConfigViewSet(viewsets.ViewSet):
    """
    ViewSet for handling S3 configuration and connection testing.
    Authentication is configurable via REQUIRE_AUTH environment variable.
    """
    # Authentication is optional - controlled by REQUIRE_AUTH setting
    permission_classes = [IsAuthenticated] if getattr(settings, 'REQUIRE_AUTH', False) else [AllowAny]
    throttle_classes = [UserRateThrottle]
    
    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        """Test AWS S3 connection."""
        # Get credentials (prefer environment variables)
        aws_access_key_id, aws_secret_access_key = get_aws_credentials(request.data)
        
        bucket_name = request.data.get('bucket_name')
        region_name = request.data.get('region_name', settings.AWS_S3_REGION_NAME)

        # Validate required fields
        if not aws_access_key_id or not aws_secret_access_key:
            return Response(
                {'error': 'AWS credentials not provided. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in environment variables or request body'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if not bucket_name:
            return Response(
                {'error': 'Bucket name is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate bucket name format
        if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', bucket_name.lower()):
            return Response(
                {'error': 'Invalid bucket name format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
            s3.head_bucket(Bucket=bucket_name)
            return Response({'message': 'S3 connection successful'}, status=status.HTTP_200_OK)
        except NoCredentialsError:
            return Response(
                {'error': 'AWS credentials not found or invalid'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            if error_code == '404' or error_code == 'NoSuchBucket':
                return Response(
                    {'error': f'Bucket "{bucket_name}" not found in region "{region_name}"'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            elif error_code == 'AccessDenied':
                return Response(
                    {'error': f'Access denied to bucket "{bucket_name}". Check permissions.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            else:
                return Response(
                    {'error': f'S3 client error: {error_message}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
