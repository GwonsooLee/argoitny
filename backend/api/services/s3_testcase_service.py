"""S3 TestCase Service for storing large test cases"""
import gzip
import json
import logging
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
import os

logger = logging.getLogger(__name__)


class S3TestCaseService:
    """Service for storing and retrieving large test cases in S3 (Singleton)"""

    # Size threshold: 100KB (conservative, allows for metadata overhead)
    SIZE_THRESHOLD_BYTES = 100 * 1024

    # Singleton instance
    _instance = None
    _initialized = False

    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(S3TestCaseService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize S3 client (only once)"""
        # Skip if already initialized
        if S3TestCaseService._initialized:
            return

        # Get bucket name from Django settings (which reads from config.yaml)
        self.bucket_name = getattr(settings, 'TESTCASE_S3_BUCKET', 'algoitny-testcases')

        # Use LocalStack for development
        localstack_url = os.getenv('LOCALSTACK_URL')

        if localstack_url:
            # LocalStack configuration
            self.s3_client = boto3.client(
                's3',
                endpoint_url=localstack_url,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            )
            logger.info(f"[S3 Init] Using LocalStack S3 at {localstack_url} with bucket '{self.bucket_name}'")
        else:
            # Production AWS configuration
            self.s3_client = boto3.client('s3')
            logger.info(f"[S3 Init] Using AWS S3 with bucket '{self.bucket_name}'")

        self._ensure_bucket_exists()

        # Mark as initialized
        S3TestCaseService._initialized = True
        logger.info(f"[S3 Init] S3TestCaseService initialized successfully")

    def _ensure_bucket_exists(self):
        """Ensure S3 bucket exists, create if not"""
        try:
            # Try to list objects instead of head_bucket (better LocalStack compatibility)
            self.s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            logger.info(f"S3 bucket '{self.bucket_name}' exists")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')

            # Handle bucket not found
            if error_code == 'NoSuchBucket' or error_code == '404':
                # Bucket doesn't exist, try to create it
                try:
                    # For LocalStack, we don't need LocationConstraint
                    localstack_url = os.getenv('LOCALSTACK_URL')
                    if localstack_url:
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        # For AWS, use LocationConstraint if not us-east-1
                        region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
                        if region == 'us-east-1':
                            self.s3_client.create_bucket(Bucket=self.bucket_name)
                        else:
                            self.s3_client.create_bucket(
                                Bucket=self.bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': region}
                            )
                    logger.info(f"Created S3 bucket '{self.bucket_name}'")
                except ClientError as create_error:
                    create_error_code = create_error.response.get('Error', {}).get('Code')
                    if create_error_code == 'BucketAlreadyOwnedByYou' or create_error_code == 'BucketAlreadyExists':
                        # Bucket already exists, this is fine
                        logger.info(f"S3 bucket '{self.bucket_name}' already exists")
                    else:
                        logger.warning(f"Could not create S3 bucket: {create_error}")
            else:
                logger.warning(f"Error checking S3 bucket: {e}")

    def _reconnect(self):
        """Reconnect to S3 in case of connection errors"""
        logger.warning("[S3 Reconnect] Attempting to reconnect to S3...")

        # Reset initialization flag to force re-initialization
        S3TestCaseService._initialized = False

        # Re-initialize
        self.__init__()

    def _execute_with_retry(self, operation, *args, **kwargs):
        """
        Execute S3 operation with automatic retry on connection errors

        Args:
            operation: The S3 operation function to execute
            *args, **kwargs: Arguments to pass to the operation

        Returns:
            Result of the operation

        Raises:
            ClientError: If operation fails after retry
        """
        try:
            return operation(*args, **kwargs)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            # Only retry on connection-related errors
            if error_code in ['RequestTimeout', 'ServiceUnavailable', 'InternalError']:
                logger.warning(f"[S3 Retry] S3 operation failed with {error_code}, reconnecting...")
                self._reconnect()
                # Retry once after reconnection
                return operation(*args, **kwargs)
            else:
                # Re-raise other errors
                raise

    @staticmethod
    def calculate_size(input_str: str, output_str: str) -> int:
        """Calculate the total size of test case data in bytes"""
        return len(input_str.encode('utf-8')) + len(output_str.encode('utf-8'))

    @staticmethod
    def should_use_s3(input_str: str, output_str: str) -> bool:
        """Determine if test case should be stored in S3"""
        size = S3TestCaseService.calculate_size(input_str, output_str)
        return size >= S3TestCaseService.SIZE_THRESHOLD_BYTES

    def _get_s3_key(self, platform: str, problem_id: str, testcase_id: str = None) -> str:
        """Generate S3 key for test cases"""
        if testcase_id:
            # Individual test case
            return f"testcases/{platform}/{problem_id}/tc_{testcase_id}.json.gz"
        else:
            # All test cases
            return f"testcases/{platform}/{problem_id}/testcases.json.gz"

    def store_testcases(
        self,
        platform: str,
        problem_id: str,
        testcases: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Store all test cases for a problem in S3 with gzip compression

        Args:
            platform: Platform name
            problem_id: Problem identifier
            testcases: List of test cases with 'testcase_id', 'input', 'output'

        Returns:
            Dict with S3 metadata: {'s3_key': str, 'size': int, 'compressed_size': int}
        """
        s3_key = self._get_s3_key(platform, problem_id)

        # Create JSON payload with all test cases
        payload = {
            'platform': platform,
            'problem_id': problem_id,
            'testcases': testcases
        }

        # Compress with gzip
        json_data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        compressed_data = gzip.compress(json_data, compresslevel=6)

        def _put_object():
            return self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=compressed_data,
                ContentType='application/json',
                ContentEncoding='gzip',
                Metadata={
                    'platform': platform,
                    'problem_id': problem_id,
                    'testcase_count': str(len(testcases))
                }
            )

        try:
            # Upload to S3 with retry
            self._execute_with_retry(_put_object)

            logger.info(
                f"Stored {len(testcases)} test cases in S3: {s3_key} "
                f"(original: {len(json_data)} bytes, compressed: {len(compressed_data)} bytes)"
            )

            return {
                's3_key': s3_key,
                'size': len(json_data),
                'compressed_size': len(compressed_data),
                'testcase_count': len(testcases)
            }

        except ClientError as e:
            logger.error(f"Failed to store test cases in S3: {e}")
            raise

    def retrieve_testcases(
        self,
        platform: str,
        problem_id: str
    ) -> List[Dict[str, str]]:
        """
        Retrieve all test cases for a problem from S3

        Args:
            platform: Platform name
            problem_id: Problem identifier

        Returns:
            List of test cases with 'testcase_id', 'input', 'output'
        """
        s3_key = self._get_s3_key(platform, problem_id)
        bucket = self.bucket_name

        def _get_object():
            return self.s3_client.get_object(Bucket=bucket, Key=s3_key)

        try:
            # Retrieve from S3 with retry
            response = self._execute_with_retry(_get_object)
            compressed_data = response['Body'].read()

            # Decompress and parse JSON
            json_data = gzip.decompress(compressed_data)
            payload = json.loads(json_data.decode('utf-8'))

            return payload.get('testcases', [])

        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == 'NoSuchKey':
                logger.warning(f"No S3 test cases found for {platform}/{problem_id}")
                return []
            logger.error(f"Failed to retrieve test cases from S3 ({s3_key}): {e}")
            raise
        except (gzip.BadGzipFile, json.JSONDecodeError) as e:
            logger.error(f"Failed to decompress/parse test cases from S3 ({s3_key}): {e}")
            raise

    def store_testcase(
        self,
        platform: str,
        problem_id: str,
        testcase_id: str,
        input_str: str,
        output_str: str
    ) -> Dict[str, Any]:
        """
        Store a single test case in S3 with gzip compression

        Args:
            platform: Platform name
            problem_id: Problem identifier
            testcase_id: Test case identifier
            input_str: Test case input
            output_str: Expected output

        Returns:
            Dict with S3 metadata: {'s3_key': str, 'size': int, 'compressed_size': int}
        """
        s3_key = self._get_s3_key(platform, problem_id, testcase_id)

        # Create JSON payload for single test case
        payload = {
            'platform': platform,
            'problem_id': problem_id,
            'testcase_id': testcase_id,
            'input': input_str,
            'output': output_str
        }

        # Compress with gzip
        json_data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        compressed_data = gzip.compress(json_data, compresslevel=6)

        def _put_object():
            return self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=compressed_data,
                ContentType='application/json',
                ContentEncoding='gzip'
            )

        try:
            # Upload to S3 with retry
            self._execute_with_retry(_put_object)

            logger.info(
                f"Stored test case in S3: {s3_key} "
                f"(original: {len(json_data)} bytes, compressed: {len(compressed_data)} bytes)"
            )

            return {
                's3_key': s3_key,
                'size': len(json_data),
                'compressed_size': len(compressed_data)
            }

        except ClientError as e:
            logger.error(f"Failed to store test case in S3: {e}")
            raise

    def retrieve_testcase(
        self,
        platform: str,
        problem_id: str,
        testcase_id: str
    ) -> Optional[Dict[str, str]]:
        """
        Retrieve a single test case from S3

        Args:
            platform: Platform name
            problem_id: Problem identifier
            testcase_id: Test case identifier

        Returns:
            Dict with 'input' and 'output', or None if not found
        """
        s3_key = self._get_s3_key(platform, problem_id, testcase_id)

        def _get_object():
            return self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)

        try:
            # Retrieve from S3 with retry
            response = self._execute_with_retry(_get_object)
            compressed_data = response['Body'].read()

            # Decompress and parse JSON
            json_data = gzip.decompress(compressed_data)
            payload = json.loads(json_data.decode('utf-8'))

            return {
                'input': payload.get('input', ''),
                'output': payload.get('output', '')
            }

        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == 'NoSuchKey':
                logger.warning(f"No S3 test case found for {platform}/{problem_id}/{testcase_id}")
                return None
            logger.error(f"Failed to retrieve test case from S3 ({s3_key}): {e}")
            raise
        except (gzip.BadGzipFile, json.JSONDecodeError) as e:
            logger.error(f"Failed to decompress/parse test case from S3 ({s3_key}): {e}")
            raise

    def delete_testcases(
        self,
        platform: str,
        problem_id: str
    ) -> bool:
        """
        Delete test cases file for a problem from S3

        Args:
            platform: Platform name
            problem_id: Problem identifier

        Returns:
            True if deleted successfully
        """
        s3_key = self._get_s3_key(platform, problem_id)

        def _delete_object():
            return self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)

        try:
            # Delete from S3 with retry
            self._execute_with_retry(_delete_object)
            logger.info(f"Deleted test cases from S3: {s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete test cases from S3 ({s3_key}): {e}")
            return False
