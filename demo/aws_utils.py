# python imports
import boto3
from botocore.exceptions import ClientError

# django imports
from django.conf import settings


aws_access_key = settings.AWS_ACCESS_KEY_ID
aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
bucket_name = settings.AWS_STORAGE_BUCKET_NAME


def upload_image(file_location, upload_location):
    try:
        s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
        
        # Upload the file to S3 bucket
        s3.upload_file(file_location, bucket_name, Key=upload_location)
        return f"https://{bucket_name}.s3.amazonaws.com/{upload_location}"
    except Exception as e:
        print(f"Error deleting file from S3: {e}")
        return False


def delete_image(file_location):
    try:
        s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
        
        # Delete the file from S3 bucket
        s3.delete_object(Bucket=bucket_name, Key=file_location)
        return True
    except Exception as e:
        print(f"Error deleting file from S3: {e}")
        return False

