import json
import os
import boto3
from botocore.exceptions import ClientError


def delete_image_from_storage(filename):
    """Delete image from Yandex Object Storage."""
    if not filename:
        return False
    
    try:
        # Get credentials from environment
        access_key_id = os.environ.get('YANDEX_ACCESS_KEY_ID')
        secret_access_key = os.environ.get('YANDEX_SECRET_ACCESS_KEY')
        bucket_name = os.environ.get('YANDEX_BUCKET_NAME')
        endpoint_url = os.environ.get('YANDEX_ENDPOINT_URL', 'https://storage.yandexcloud.net')
        region = os.environ.get('YANDEX_REGION', 'ru-central1')
        
        if not all([access_key_id, secret_access_key, bucket_name]):
            print(f'Missing required environment variables')
            return False
        
        # Create S3 client
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region
        )
        
        # Delete object
        s3.delete_object(Bucket=bucket_name, Key=filename)
        print(f'Successfully deleted: {filename}')
        return True
    
    except ClientError as e:
        print(f'Error deleting image {filename}: {e}')
        return False
    except Exception as e:
        print(f'Unexpected error: {e}')
        return False


def handler(event, context):
    """Cloud Function handler for Yandex Message Queue trigger."""
    # Parse the message body
    try:
        # The message body contains the filename
        filename = None
        
        if isinstance(event, dict):
            # Check for different message formats
            if 'messages' in event:
                # Yandex Message Queue format
                for message in event['messages']:
                    if 'body' in message:
                        filename = message['body']
                        break
            elif 'body' in event:
                # Direct body
                filename = event['body']
            else:
                # Try to parse as JSON
                filename = json.loads(json.dumps(event))
        
        if not filename:
            print('No filename found in event')
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No filename provided'})
            }
        
        # Delete the image
        success = delete_image_from_storage(filename)
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({'message': f'Successfully deleted: {filename}'})
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f'Failed to delete: {filename}'})
            }
    
    except Exception as e:
        print(f'Error processing event: {e}')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }