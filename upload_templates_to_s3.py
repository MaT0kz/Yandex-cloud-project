#!/usr/bin/env python3
"""
Script to upload HTML templates to Yandex Object Storage static pages bucket.
This script renders templates with sample data and uploads them to S3.

Usage:
    python upload_templates_to_s3.py

Environment variables required:
    - YANDEX_ACCESS_KEY_ID
    - YANDEX_SECRET_ACCESS_KEY
    - YANDEX_ENDPOINT_URL (default: https://storage.yandexcloud.net)
    - YANDEX_REGION (default: ru-central1)
    - STATIC_PAGES_BUCKET_NAME (default: news-site-pages)
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError

# Templates to upload (without .html extension)
TEMPLATES = [
    'index',
    'register',
    'login',
    'create',
    'edit',
    'view',
    'my_news',
    '404',
    '500',
]


def get_s3_client():
    """Get S3 client configured for Yandex Object Storage."""
    return boto3.client(
        's3',
        endpoint_url=os.environ.get('YANDEX_ENDPOINT_URL', 'https://storage.yandexcloud.net'),
        aws_access_key_id=os.environ.get('YANDEX_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('YANDEX_SECRET_ACCESS_KEY'),
        region_name=os.environ.get('YANDEX_REGION', 'ru-central1')
    )


def upload_file_to_s3(s3_client, bucket_name, file_path, object_name=None):
    """Upload a file to S3 bucket."""
    if object_name is None:
        object_name = os.path.basename(file_path)

    try:
        s3_client.upload_file(file_path, bucket_name, object_name)
        print(f'  ✓ Uploaded: {object_name}')
        return True
    except ClientError as e:
        print(f'  ✗ Error uploading {object_name}: {e}')
        return False


def main():
    """Main function to upload all templates to S3."""
    print('=' * 60)
    print('Upload HTML Templates to Yandex Object Storage')
    print('=' * 60)

    # Get configuration
    bucket_name = os.environ.get('STATIC_PAGES_BUCKET_NAME', 'news-site-pages')
    templates_dir = os.path.join(os.path.dirname(__file__), 'app', 'templates')

    print(f'\nConfiguration:')
    print(f'  Bucket: {bucket_name}')
    print(f'  Templates dir: {templates_dir}')

    # Check environment variables
    if not os.environ.get('YANDEX_ACCESS_KEY_ID'):
        print('\n✗ Error: YANDEX_ACCESS_KEY_ID environment variable not set')
        sys.exit(1)

    if not os.environ.get('YANDEX_SECRET_ACCESS_KEY'):
        print('\n✗ Error: YANDEX_SECRET_ACCESS_KEY environment variable not set')
        sys.exit(1)

    # Get S3 client
    try:
        s3_client = get_s3_client()
        print('\n✓ Connected to Yandex Object Storage')
    except Exception as e:
        print(f'\n✗ Error connecting to S3: {e}')
        sys.exit(1)

    # Check if bucket exists
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f'✓ Bucket "{bucket_name}" exists')
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404':
            print(f'\n✗ Bucket "{bucket_name}" does not exist')
            print('  Please create the bucket first:')
            print(f'  yc storage bucket create --name {bucket_name}')
        else:
            print(f'\n✗ Error checking bucket: {e}')
        sys.exit(1)

    # Upload templates
    print(f'\nUploading templates to bucket "{bucket_name}":')
    print('-' * 60)

    success_count = 0
    error_count = 0

    for template_name in TEMPLATES:
        template_path = os.path.join(templates_dir, f'{template_name}.html')
        object_name = f'{template_name}.html'

        if os.path.exists(template_path):
            if upload_file_to_s3(s3_client, bucket_name, template_path, object_name):
                success_count += 1
            else:
                error_count += 1
        else:
            print(f'  - Skipped: {template_name}.html (not found)')
            error_count += 1

    # Summary
    print('-' * 60)
    print(f'\nSummary:')
    print(f'  Uploaded: {success_count}')
    print(f'  Errors: {error_count}')
    print(f'  Total: {success_count + error_count}')

    if error_count == 0:
        print('\n✓ All templates uploaded successfully!')
        print(f'\nStatic pages URL: https://storage.yandexcloud.net/{bucket_name}/')
    else:
        print('\n⚠ Some templates failed to upload')
        sys.exit(1)


if __name__ == '__main__':
    main()