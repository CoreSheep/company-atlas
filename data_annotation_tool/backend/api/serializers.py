from rest_framework import serializers


class CSVUploadSerializer(serializers.Serializer):
    file = serializers.FileField()


class CSVSaveSerializer(serializers.Serializer):
    filename = serializers.CharField()
    headers = serializers.ListField(child=serializers.CharField())
    rows = serializers.ListField(child=serializers.DictField())


class S3ConfigSerializer(serializers.Serializer):
    aws_access_key_id = serializers.CharField()
    aws_secret_access_key = serializers.CharField()
    bucket_name = serializers.CharField()
    region_name = serializers.CharField(default='us-east-1')

