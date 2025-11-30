import csv
import io
import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser
from django.conf import settings
import os
from datetime import datetime


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
    """
    parser_classes = [MultiPartParser, JSONParser]

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload a CSV file."""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']
        
        if not file.name.endswith('.csv'):
            return Response(
                {'error': 'File must be a CSV file'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Read CSV content
            decoded_file = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded_file))
            rows = list(csv_reader)
            
            if not rows:
                return Response(
                    {'error': 'CSV file is empty'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            headers = list(rows[0].keys())

            return Response({
                'filename': file.name,
                'headers': headers,
                'rows': rows,
                'row_count': len(rows),
            }, status=status.HTTP_200_OK)
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

        if not headers or not rows:
            return Response(
                {'error': 'No data to save'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['post'])
    def upload_to_s3(self, request):
        """Upload edited CSV data to S3."""
        aws_access_key_id = request.data.get('aws_access_key_id')
        aws_secret_access_key = request.data.get('aws_secret_access_key')
        bucket_name = request.data.get('bucket_name')
        region_name = request.data.get('region_name')
        s3_key = request.data.get('s3_key')
        filename = request.data.get('filename', 'edited_data.csv')
        headers = request.data.get('headers', [])
        rows = request.data.get('rows', [])

        if not all([aws_access_key_id, aws_secret_access_key, bucket_name, region_name, s3_key]):
            return Response(
                {'error': 'Missing S3 configuration or S3 Key'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if not headers or not rows:
            return Response(
                {'error': 'No data to upload'}, 
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
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
            csv_content = output.getvalue()

            s3.put_object(Bucket=bucket_name, Key=s3_key, Body=csv_content, ContentType='text/csv')
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
            return Response(
                {'error': f'S3 client error: {e}'}, 
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
    """
    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        """Test AWS S3 connection."""
        aws_access_key_id = request.data.get('aws_access_key_id')
        aws_secret_access_key = request.data.get('aws_secret_access_key')
        bucket_name = request.data.get('bucket_name')
        region_name = request.data.get('region_name')

        if not all([aws_access_key_id, aws_secret_access_key, bucket_name, region_name]):
            return Response(
                {'error': 'Missing AWS credentials or bucket name'}, 
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
            if e.response['Error']['Code'] == '404':
                return Response(
                    {'error': f'Bucket "{bucket_name}" not found in region "{region_name}"'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            elif e.response['Error']['Code'] == 'AccessDenied':
                return Response(
                    {'error': f'Access denied to bucket "{bucket_name}". Check permissions.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            else:
                return Response(
                    {'error': f'S3 client error: {e}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
