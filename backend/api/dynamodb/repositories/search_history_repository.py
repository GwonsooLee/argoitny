"""SearchHistory repository for DynamoDB operations - New Model"""
import time
import base64
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from .base_repository import BaseRepository


class SearchHistoryRepository(BaseRepository):
    """
    Repository for SearchHistory entity - New ID-based model

    Entity Pattern:
    - PK: HIST#{history_id}
    - SK: META
    - tp: hist
    - dat: {
        'uid': user_id,
        'uidt': user_identifier/email,
        'pid': problem_id (optional),
        'plt': platform,
        'pno': problem_number,
        'ptt': problem_title,
        'lng': language,
        'cod': code,
        'res': result_summary,
        'psc': passed_count,
        'fsc': failed_count,
        'toc': total_count,
        'pub': is_code_public,
        'trs': test_results (optional),
        'hnt': hints (optional),
        'met': metadata (optional)
    }
    - crt: created_timestamp
    - upd: updated_timestamp
    - GSI1PK: USER#{user_id} (for user queries)
    - GSI1SK: HIST#{timestamp}
    - GSI2PK: PUBLIC#HIST (for public queries, if is_code_public=True)
    - GSI2SK: {timestamp}

    Example item:
    {
        'PK': 'HIST#1760106824998921',
        'SK': 'META',
        'tp': 'hist',
        'dat': {
            'uid': 123,
            'uidt': 'user@example.com',
            'pid': 456,
            'plt': 'baekjoon',
            'pno': '1000',
            'ptt': 'A+B',
            'lng': 'python',
            'cod': 'cHJpbnQoLi4uKQ==',  # base64 encoded
            'res': 'passed',
            'psc': 95,
            'fsc': 5,
            'toc': 100,
            'pub': True,
            'trs': [...],
            'hnt': ['hint1']
        },
        'crt': 1760106824998,
        'upd': 1760106824998,
        'GSI1PK': 'USER#123',
        'GSI1SK': 'HIST#1760106824998',
        'GSI2PK': 'PUBLIC#HIST',
        'GSI2SK': '1760106824998'
    }
    """

    def __init__(self, table=None):
        if table is None:
            from ..client import DynamoDBClient
            table = DynamoDBClient.get_table()
        super().__init__(table)
        self._counter_repo = None

        # S3 client for large test results offloading
        import boto3
        import os
        self.s3_client = boto3.client('s3', endpoint_url=os.getenv('S3_ENDPOINT_URL'))
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'algoitny-history-results')

    def _get_counter_repo(self):
        """Lazy load counter repository"""
        if self._counter_repo is None:
            from .counter_repository import CounterRepository
            self._counter_repo = CounterRepository(self.table)
        return self._counter_repo

    def get_history(self, history_id: int) -> Optional[Dict]:
        """
        Get history by ID

        Args:
            history_id: History ID

        Returns:
            DynamoDB item or None if not found
        """
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'HIST#{history_id}',
                    'SK': 'META'
                }
            )
            return response.get('Item')
        except Exception:
            return None

    def get_history_with_testcases(self, history_id: int) -> Optional[Dict]:
        """
        Get history with test cases

        Args:
            history_id: History ID

        Returns:
            DynamoDB item or None if not found
            Note: Test results may be loaded from S3 if offloaded
        """
        import logging
        logger = logging.getLogger(__name__)

        item = self.get_history(history_id)
        if not item:
            return None

        # Decode base64-encoded code
        cod = item.get('dat', {}).get('cod', '')
        if cod:
            try:
                item['dat']['cod'] = base64.b64decode(cod.encode('utf-8')).decode('utf-8')
            except Exception:
                # If decoding fails, keep the original value (backward compatibility)
                pass

        # Load from S3 if test results are offloaded
        trs = item.get('dat', {}).get('trs')
        if isinstance(trs, dict) and 's3' in trs:
            import gzip
            import json

            try:
                obj = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=trs['s3']
                )
                compressed = obj['Body'].read()
                decompressed = gzip.decompress(compressed).decode()
                item['dat']['trs'] = json.loads(decompressed)
                logger.info(f"Loaded test results from S3: {trs['s3']}")
            except Exception as e:
                logger.error(f"Failed to load test results from S3: {e}")
                item['dat']['trs'] = []

        return item

    def list_user_history(
        self,
        user_id: int,
        limit: int = 20,
        last_evaluated_key: Optional[Dict] = None
    ) -> Tuple[List[Dict], Optional[Dict]]:
        """
        List user's history with pagination

        Args:
            user_id: User ID
            limit: Max items to return
            last_evaluated_key: Pagination key

        Returns:
            Tuple of (items, next_key)
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            query_params = {
                'IndexName': 'GSI1',
                'KeyConditionExpression': Key('GSI1PK').eq(f'USER#{user_id}') & Key('GSI1SK').begins_with('HIST#'),
                'Limit': limit,
                'ScanIndexForward': False  # Newest first
            }

            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key

            logger.info(f"[SearchHistory] Querying user history: user_id={user_id}, limit={limit}")
            response = self.table.query(**query_params)
            items = response.get('Items', [])
            next_key = response.get('LastEvaluatedKey')

            logger.info(f"[SearchHistory] Query returned {len(items)} items")

            return items, next_key
        except Exception as e:
            logger.error(f"[SearchHistory] Failed to list user history: {str(e)}", exc_info=True)
            return [], None

    def list_public_history(
        self,
        limit: int = 20,
        last_evaluated_key: Optional[Dict] = None
    ) -> Tuple[List[Dict], Optional[Dict]]:
        """
        List public history with pagination

        Args:
            limit: Max items to return
            last_evaluated_key: Pagination key

        Returns:
            Tuple of (items, next_key)
        """
        try:
            query_params = {
                'IndexName': 'GSI2',
                'KeyConditionExpression': Key('GSI2PK').eq('PUBLIC#HIST'),
                'Limit': limit,
                'ScanIndexForward': False  # Newest first
            }

            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key

            response = self.table.query(**query_params)
            items = response.get('Items', [])
            next_key = response.get('LastEvaluatedKey')

            return items, next_key
        except Exception:
            return [], None

    def list_public_history_by_partition(
        self,
        partition: str,
        limit: int = 20,
        last_evaluated_key: Optional[Dict] = None
    ) -> Tuple[List[Dict], Optional[Dict]]:
        """
        List public history for a specific time partition

        Args:
            partition: Time partition (format: YYYYMMDDHH)
            limit: Max items to return
            last_evaluated_key: Pagination key

        Returns:
            Tuple of (items, next_key)

        Performance:
            - Solves GSI2 hot partition issue by distributing writes across hourly partitions
            - Queries specific time partition instead of single 'PUBLIC#HIST' partition
        """
        try:
            query_params = {
                'IndexName': 'GSI2',
                'KeyConditionExpression': Key('GSI2PK').eq(f'PUBLIC#HIST#{partition}'),
                'Limit': limit,
                'ScanIndexForward': False  # Newest first
            }

            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key

            response = self.table.query(**query_params)
            items = response.get('Items', [])
            next_key = response.get('LastEvaluatedKey')

            return items, next_key
        except Exception:
            return [], None

    def create_history(
        self,
        user_id: int,
        user_identifier: str,
        platform: str,
        problem_number: str,
        problem_title: str,
        language: str,
        code: str,
        result_summary: str,
        passed_count: int,
        failed_count: int,
        total_count: int,
        is_code_public: bool = False,
        problem_id: Optional[int] = None,
        test_results: Optional[List[Dict]] = None,
        hints: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a new history entry

        Args:
            user_id: User ID
            user_identifier: User email or identifier
            platform: Platform name
            problem_number: Problem number/identifier
            problem_title: Problem title
            language: Programming language
            code: User's code
            result_summary: Overall result (passed/failed)
            passed_count: Number of passed tests
            failed_count: Number of failed tests
            total_count: Total number of tests
            is_code_public: Whether code is public
            problem_id: Problem ID (optional)
            test_results: List of test results (optional)
            hints: List of hints (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created history item
        """
        # Generate unique history ID using counter
        counter_repo = self._get_counter_repo()
        history_id = counter_repo.get_next_id('search_history')

        timestamp = int(time.time())

        # Base64 encode the code
        encoded_code = base64.b64encode(code.encode('utf-8')).decode('utf-8')

        # Prepare data object with short field names
        dat = {
            'uid': user_id,
            'uidt': user_identifier,
            'plt': platform,
            'pno': problem_number,
            'ptt': problem_title,
            'lng': language,
            'cod': encoded_code,
            'res': result_summary,
            'psc': passed_count,
            'fsc': failed_count,
            'toc': total_count,
            'pub': is_code_public,
        }

        if problem_id is not None:
            dat['pid'] = problem_id

        # S3 offloading for large test results (>10KB)
        if test_results:
            import gzip
            import json

            test_results_json = json.dumps(test_results)
            if len(test_results_json.encode()) > 10240:  # 10KB threshold
                # Upload to S3 with compression
                s3_key = f"results/{str(history_id)[:8]}/{history_id}/test_results.json.gz"
                compressed = gzip.compress(test_results_json.encode())

                try:
                    self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=s3_key,
                        Body=compressed,
                        ContentType='application/json',
                        ContentEncoding='gzip'
                    )

                    # Store S3 reference instead of full data
                    dat['trs'] = {'s3': s3_key, 'cnt': len(test_results)}
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to upload test results to S3: {e}")
                    # Fallback to storing in DynamoDB
                    dat['trs'] = test_results
            else:
                # Small results stored directly in DynamoDB
                dat['trs'] = test_results

        if hints:
            dat['hnt'] = hints
        if metadata:
            dat['met'] = metadata

        # Build item
        item = {
            'PK': f'HIST#{history_id}',
            'SK': 'META',
            'tp': 'hist',
            'dat': dat,
            'crt': timestamp,
            'upd': timestamp,
            'GSI1PK': f'USER#{user_id}',
            'GSI1SK': f'HIST#{timestamp}'
        }

        # Add public GSI if code is public
        if is_code_public:
            item['GSI2PK'] = 'PUBLIC#HIST'
            item['GSI2SK'] = str(timestamp)

        self.put_item(item)
        return item

    def update_history(self, history_id: int, updates: Dict) -> bool:
        """
        Update history entry

        Args:
            history_id: History ID
            updates: Dict of fields to update (using short field names)
                Examples: {'hnt': ['hint1'], 'pub': True}

        Returns:
            True if updated successfully
        """
        try:
            # Build update expression
            update_parts = []
            expression_values = {}

            for key, value in updates.items():
                update_parts.append(f'dat.{key} = :{key}')
                expression_values[f':{key}'] = value

            # Always update timestamp
            update_parts.append('upd = :upd')
            expression_values[':upd'] = int(time.time())

            update_expression = 'SET ' + ', '.join(update_parts)

            self.table.update_item(
                Key={
                    'PK': f'HIST#{history_id}',
                    'SK': 'META'
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            return True
        except Exception:
            return False

    def count_unique_problems(self, user_id: int) -> int:
        """
        Count unique problems tested by user (optimized with UserStats)

        Args:
            user_id: User ID

        Returns:
            Count of unique problems

        Performance:
            - Before: 125 RCU (scanning all history)
            - After: 0.5 RCU (single GetItem from UserStats)
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            from .user_stats_repository import UserStatsRepository
            stats_repo = UserStatsRepository(self.table)
            return stats_repo.count_unique_problems(user_id)
        except Exception as e:
            logger.warning(f"Failed to get stats, falling back to legacy method: {e}")

            # Fallback to legacy method (expensive)
            try:
                items, _ = self.list_user_history(user_id, limit=1000)
                unique_problems = set()
                for item in items:
                    dat = item.get('dat', {})
                    platform = dat.get('plt')
                    problem_number = dat.get('pno')
                    if platform and problem_number:
                        unique_problems.add(f'{platform}#{problem_number}')
                return len(unique_problems)
            except Exception:
                return 0

    # Legacy methods for backward compatibility (deprecated)
    def create_search_history(
        self,
        email: str,
        platform: str,
        problem_number: str,
        problem_title: str,
        code: Optional[str] = None,
        is_code_public: bool = False,
        hints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Legacy method - creates history with old model
        DEPRECATED: Use create_history instead
        """
        # For backward compatibility, create with minimal data
        return self.create_history(
            user_id=0,  # No user_id in legacy model
            user_identifier=email,
            platform=platform,
            problem_number=problem_number,
            problem_title=problem_title,
            language='unknown',
            code=code or '',
            result_summary='unknown',
            passed_count=0,
            failed_count=0,
            total_count=0,
            is_code_public=is_code_public,
            hints=hints
        )

    def get_user_search_history(
        self,
        email: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Legacy method - get user history by email
        DEPRECATED: Use list_user_history with user_id
        """
        # This is tricky since we don't have email index
        # Return empty for now
        return []

    def get_user_problem_history(
        self,
        email: str,
        platform: str,
        problem_number: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Legacy method
        DEPRECATED
        """
        return []

    def get_public_history(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Legacy method
        DEPRECATED: Use list_public_history
        """
        items, _ = self.list_public_history(limit=limit)
        return items

    def update_hints(
        self,
        email: str,
        platform: str,
        problem_number: str,
        timestamp: int,
        hints: List[str]
    ) -> bool:
        """
        Legacy method
        DEPRECATED: Use update_history with history_id
        """
        return False
