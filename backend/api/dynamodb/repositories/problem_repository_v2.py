"""Problem repository for DynamoDB operations with S3 test case storage"""
from typing import Dict, Optional, List, Any
from boto3.dynamodb.conditions import Key, Attr
from .base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)


class ProblemRepositoryV2(BaseRepository):
    """Repository for Problem operations with all test cases stored in S3"""

    def __init__(self, table=None, s3_service=None):
        """
        Initialize ProblemRepositoryV2

        Args:
            table: DynamoDB table resource. If None, will be fetched from DynamoDBClient
            s3_service: S3TestCaseService instance. If None, will be created
        """
        if table is None:
            from ..client import DynamoDBClient
            table = DynamoDBClient.get_table()
        super().__init__(table)

        # Initialize S3 service for test cases
        if s3_service is None:
            from api.services.s3_testcase_service import S3TestCaseService
            s3_service = S3TestCaseService()
        self.s3_service = s3_service

    def add_testcases_batch(
        self,
        platform: str,
        problem_id: str,
        testcases: List[Dict[str, str]]
    ) -> bool:
        """
        Add all test cases for a problem to S3 in a single file
        Updates problem metadata to indicate S3 storage

        Args:
            platform: Platform name
            problem_id: Problem identifier
            testcases: List of test cases with 'testcase_id', 'input', 'output'

        Returns:
            True if successful
        """
        try:
            # Store all test cases in S3
            s3_metadata = self.s3_service.store_testcases(
                platform=platform,
                problem_id=problem_id,
                testcases=testcases
            )

            # Update problem metadata to indicate S3 storage
            self.update_problem(
                platform=platform,
                problem_id=problem_id,
                updates={
                    'test_case_count': len(testcases),
                    'testcases_in_s3': True
                }
            )

            logger.info(
                f"Stored {len(testcases)} test cases in S3 for {platform}/{problem_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store test cases: {e}")
            return False

    def get_testcases(
        self,
        platform: str,
        problem_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all test cases for a problem from S3

        Args:
            platform: Platform name
            problem_id: Problem identifier

        Returns:
            List of test case dictionaries
        """
        try:
            testcases = self.s3_service.retrieve_testcases(
                platform=platform,
                problem_id=problem_id
            )
            return testcases

        except Exception as e:
            logger.error(f"Failed to retrieve test cases: {e}")
            return []

    def delete_problem(
        self,
        platform: str,
        problem_id: str
    ) -> bool:
        """
        Delete problem metadata from DynamoDB and test cases from S3

        Args:
            platform: Platform name
            problem_id: Problem identifier

        Returns:
            True if deleted successfully
        """
        pk = f'PROB#{platform}#{problem_id}'

        # Delete DynamoDB item
        success = self.delete_item(pk, 'META')

        # Delete S3 test cases
        try:
            self.s3_service.delete_testcases(platform, problem_id)
        except Exception as e:
            logger.error(f"Failed to delete S3 test cases: {e}")
            success = False

        return success
