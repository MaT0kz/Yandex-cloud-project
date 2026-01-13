#!/usr/bin/env python3
"""
Скрипт для загрузки HTML-шаблонов в Yandex Object Storage.
"""

import os
import boto3
from botocore.exceptions import ClientError

# ==================== ПЕРЕМЕННЫЕ ====================
# Задайте значения здесь или используйте переменные окружения

# Имя бакета для страниц
PAGES_BUCKET_NAME = os.environ.get('STATIC_PAGES_BUCKET_NAME', 'news-site-pages')

# Путь к директории с шаблонами
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'app', 'templates')

# Yandex Cloud credentials
YANDEX_ACCESS_KEY_ID = os.environ.get('YANDEX_ACCESS_KEY_ID')
YANDEX_SECRET_ACCESS_KEY = os.environ.get('YANDEX_SECRET_ACCESS_KEY')
YANDEX_ENDPOINT_URL = os.environ.get('YANDEX_ENDPOINT_URL', 'https://storage.yandexcloud.net')
YANDEX_REGION = os.environ.get('YANDEX_REGION', 'ru-central1')

# Шаблоны для загрузки (без .html)
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

# ==================== СКРИПТ ====================

def get_s3_client():
    """Создание S3 клиента."""
    return boto3.client(
        's3',
        endpoint_url=YANDEX_ENDPOINT_URL,
        aws_access_key_id=YANDEX_ACCESS_KEY_ID,
        aws_secret_access_key=YANDEX_SECRET_ACCESS_KEY,
        region_name=YANDEX_REGION
    )


def upload_template(s3_client, template_name):
    """Загрузка одного шаблона в бакет."""
    file_path = os.path.join(TEMPLATES_DIR, f'{template_name}.html')
    object_name = f'{template_name}.html'
    
    try:
        s3_client.upload_file(file_path, PAGES_BUCKET_NAME, object_name)
        print(f'  ✓ {object_name}')
        return True
    except ClientError as e:
        print(f'  ✗ {object_name}: {e}')
        return False


def main():
    """Основная функция."""
    print(f'Загрузка шаблонов в бакет: {PAGES_BUCKET_NAME}')
    print(f'Директория: {TEMPLATES_DIR}')
    print()
    
    if not YANDEX_ACCESS_KEY_ID or not YANDEX_SECRET_ACCESS_KEY:
        print('Ошибка: задайте YANDEX_ACCESS_KEY_ID и YANDEX_SECRET_ACCESS_KEY')
        print('Через переменные окружения или в начале скрипта')
        return
    
    s3_client = get_s3_client()
    
    print('Загрузка:')
    success = 0
    for template in TEMPLATES:
        if upload_template(s3_client, template):
            success += 1
    
    print()
    print(f'Загружено: {success}/{len(TEMPLATES)}')
    print(f'URL бакета: {YANDEX_ENDPOINT_URL}/{PAGES_BUCKET_NAME}')


if __name__ == '__main__':
    main()