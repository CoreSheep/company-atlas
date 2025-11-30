from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CSVFileViewSet, S3ConfigViewSet

router = DefaultRouter()
router.register(r'files', CSVFileViewSet, basename='csvfile')
router.register(r's3-config', S3ConfigViewSet, basename='s3config')

urlpatterns = [
    path('', include(router.urls)),
]

