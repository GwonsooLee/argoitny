"""Problem repository for DynamoDB operations"""
from typing import Dict, Optional, List, Any
from boto3.dynamodb.conditions import Key, Attr
from .base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)


class ProblemRepository(BaseRepository):
    """Repository for Problem and TestCase operations"""

    def __init__(self, table=None, s3_service=None):
        """
        Initialize ProblemRepository

        Args:
            table: DynamoDB table resource. If None, will be fetched from DynamoDBClient
            s3_service: S3TestCaseService instance. If None, will be created
        """
        if table is None:
            from ..client import DynamoDBClient
            table = DynamoDBClient.get_table()
        super().__init__(table)

        # Initialize S3 service for large test cases
        if s3_service is None:
            from api.services.s3_testcase_service import S3TestCaseService
            s3_service = S3TestCaseService()
        self.s3_service = s3_service

    def create_problem(
        self,
        platform: str,
        problem_id: str,
        problem_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new problem

        Args:
            platform: Platform name (e.g., 'baekjoon', 'leetcode')
            problem_id: Problem identifier on the platform
            problem_data: Problem data with fields:
                - title: Problem title (required)
                - problem_url: URL to the problem (optional)
                - tags: List of tags (optional)
                - solution_code: Solution code (optional)
                - language: Programming language (optional)
                - constraints: Problem constraints (optional)
                - is_completed: Completion status (default: False)
                - is_deleted: Deletion status (default: False)
                - deleted_at: Deletion timestamp (optional)
                - deleted_reason: Reason for deletion (optional)
                - needs_review: Review flag (default: False)
                - review_notes: Review notes (optional)
                - verified_by_admin: Admin verification flag (default: False)
                - reviewed_at: Review timestamp (optional)
                - metadata: Additional metadata (optional)

        Returns:
            Created problem item
        """
        timestamp = self.get_timestamp()

        # Encode solution_code to base64 if present
        import base64
        solution_code = problem_data.get('solution_code', '')
        solution_code_encoded = base64.b64encode(solution_code.encode('utf-8')).decode('utf-8') if solution_code else ''

        # Build dat map with short field names
        dat = {
            'tit': problem_data.get('title', ''),
            'url': problem_data.get('problem_url', ''),
            'tag': problem_data.get('tags', []),
            'sol': solution_code_encoded,
            'lng': problem_data.get('language', ''),
            'con': problem_data.get('constraints', ''),
            'cmp': problem_data.get('is_completed', False),
            'tcc': problem_data.get('test_case_count', 0),  # Test case count
            'del': problem_data.get('is_deleted', False),
            'nrv': problem_data.get('needs_review', False),
            'vrf': problem_data.get('verified_by_admin', False)
        }

        # Add optional fields only if provided
        if problem_data.get('deleted_at'):
            dat['ddt'] = problem_data['deleted_at']
        if problem_data.get('deleted_reason'):
            dat['drs'] = problem_data['deleted_reason']
        if problem_data.get('review_notes'):
            dat['rvn'] = problem_data['review_notes']
        if problem_data.get('reviewed_at'):
            dat['rvt'] = problem_data['reviewed_at']
        if problem_data.get('metadata'):
            dat['met'] = problem_data['metadata']

        # Set GSI3 for problem status indexing
        gsi3pk = 'PROB#COMPLETED' if dat.get('cmp') else 'PROB#DRAFT'

        item = {
            'PK': f'PROB#{platform}#{problem_id}',
            'SK': 'META',
            'tp': 'prob',
            'dat': dat,
            'crt': timestamp,
            'upd': timestamp,
            'GSI3PK': gsi3pk,
            'GSI3SK': timestamp
        }

        return self.put_item(item)

    def get_problem(
        self,
        platform: str,
        problem_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get problem metadata (without test cases)

        Args:
            platform: Platform name
            problem_id: Problem identifier

        Returns:
            Problem item or None if not found
        """
        pk = f'PROB#{platform}#{problem_id}'
        sk = 'META'

        item = self.get_item(pk, sk)
        if not item:
            return None

        # Expand short field names for easier consumption
        if item.get('dat'):
            # Decode solution_code from base64
            import base64
            solution_code_encoded = item['dat'].get('sol', '')
            solution_code = base64.b64decode(solution_code_encoded).decode('utf-8') if solution_code_encoded else ''

            problem = {
                'platform': platform,
                'problem_id': problem_id,
                'title': item['dat'].get('tit', ''),
                'problem_url': item['dat'].get('url', ''),
                'tags': item['dat'].get('tag', []),
                'solution_code': solution_code,
                'language': item['dat'].get('lng', ''),
                'constraints': item['dat'].get('con', ''),
                'is_completed': item['dat'].get('cmp', False),
                'test_case_count': item['dat'].get('tcc', 0),
                'testcases': item['dat'].get('tcs', []),  # Include testcases from dat
                'is_deleted': item['dat'].get('del', False),
                'deleted_at': item['dat'].get('ddt'),
                'deleted_reason': item['dat'].get('drs'),
                'needs_review': item['dat'].get('nrv', False),
                'review_notes': item['dat'].get('rvn'),
                'verified_by_admin': item['dat'].get('vrf', False),
                'reviewed_at': item['dat'].get('rvt'),
                'metadata': item['dat'].get('met', {}),
                'created_at': item.get('crt'),
                'updated_at': item.get('upd')
            }
            return problem

        return None

    def get_problem_with_testcases(
        self,
        platform: str,
        problem_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get problem with all test cases

        Args:
            platform: Platform name
            problem_id: Problem identifier

        Returns:
            Problem dict with test_cases list, or None if not found
        """
        pk = f'PROB#{platform}#{problem_id}'

        items = self.query(
            key_condition_expression=Key('PK').eq(pk)
        )

        if not items:
            return None

        problem = None
        test_cases = []

        for item in items:
            if item.get('SK') == 'META':
                # Problem metadata
                # Decode solution_code from base64
                import base64
                solution_code_encoded = item['dat'].get('sol', '')
                solution_code = base64.b64decode(solution_code_encoded).decode('utf-8') if solution_code_encoded else ''

                problem = {
                    'platform': platform,
                    'problem_id': problem_id,
                    'title': item['dat'].get('tit', ''),
                    'problem_url': item['dat'].get('url', ''),
                    'tags': item['dat'].get('tag', []),
                    'solution_code': solution_code,
                    'language': item['dat'].get('lng', ''),
                    'constraints': item['dat'].get('con', ''),
                    'is_completed': item['dat'].get('cmp', False),
                    'test_case_count': item['dat'].get('tcc', 0),
                    'testcases': item['dat'].get('tcs', []),  # Include testcases from dat
                    'is_deleted': item['dat'].get('del', False),
                    'deleted_at': item['dat'].get('ddt'),
                    'deleted_reason': item['dat'].get('drs'),
                    'needs_review': item['dat'].get('nrv', False),
                    'review_notes': item['dat'].get('rvn'),
                    'verified_by_admin': item['dat'].get('vrf', False),
                    'reviewed_at': item['dat'].get('rvt'),
                    'metadata': item['dat'].get('met', {}),
                    'created_at': item.get('crt'),
                    'updated_at': item.get('upd')
                }

        # Return problem with testcases
        if problem:
            # Load test cases using get_testcases method (handles TC# items and S3)
            try:
                test_cases = self.get_testcases(platform, problem_id)
                problem['test_cases'] = test_cases
            except Exception as e:
                logger.warning(f"Failed to load testcases for {platform}/{problem_id}: {e}")
                problem['test_cases'] = []

            return problem

        return None

    def update_problem(
        self,
        platform: str,
        problem_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update problem metadata

        Args:
            platform: Platform name
            problem_id: Problem identifier
            updates: Dictionary of fields to update (uses long field names):
                - title, problem_url, tags, solution_code, language,
                  constraints, is_completed, is_deleted, deleted_at,
                  deleted_reason, needs_review, review_notes,
                  verified_by_admin, reviewed_at, metadata

        Returns:
            Updated problem item
        """
        pk = f'PROB#{platform}#{problem_id}'
        sk = 'META'

        # Map long field names to short field names
        field_mapping = {
            'title': 'tit',
            'problem_url': 'url',
            'tags': 'tag',
            'solution_code': 'sol',
            'language': 'lng',
            'constraints': 'con',
            'is_completed': 'cmp',
            'test_case_count': 'tcc',
            'testcases': 'tcs',  # Test cases stored in Problem dat
            'is_deleted': 'del',
            'deleted_at': 'ddt',
            'deleted_reason': 'drs',
            'needs_review': 'nrv',
            'review_notes': 'rvn',
            'verified_by_admin': 'vrf',
            'reviewed_at': 'rvt',
            'metadata': 'met'
        }

        # Build update expression
        update_parts = []
        expression_values = {}
        expression_names = {}

        # Encode solution_code to base64 if present in updates
        import base64
        if 'solution_code' in updates:
            solution_code = updates['solution_code']
            updates['solution_code'] = base64.b64encode(solution_code.encode('utf-8')).decode('utf-8') if solution_code else ''

        for long_name, value in updates.items():
            if long_name in field_mapping:
                short_name = field_mapping[long_name]
                # Use attribute names to handle reserved words
                attr_placeholder = f'#{short_name}'
                val_placeholder = f':{short_name}'

                update_parts.append(f'dat.{attr_placeholder} = {val_placeholder}')
                expression_values[val_placeholder] = value
                expression_names[attr_placeholder] = short_name

        # Update GSI3PK when is_completed changes
        if 'is_completed' in updates:
            gsi3pk = 'PROB#COMPLETED' if updates['is_completed'] else 'PROB#DRAFT'
            update_parts.append('#gsi3pk = :gsi3pk')
            expression_values[':gsi3pk'] = gsi3pk
            expression_names['#gsi3pk'] = 'GSI3PK'

        # Always update the 'upd' timestamp
        update_parts.append('#upd = :upd')
        expression_values[':upd'] = self.get_timestamp()
        expression_names['#upd'] = 'upd'

        if not update_parts:
            # No updates to apply
            return self.get_item(pk, sk)

        update_expression = 'SET ' + ', '.join(update_parts)

        return self.update_item(
            pk=pk,
            sk=sk,
            update_expression=update_expression,
            expression_attribute_values=expression_values,
            expression_attribute_names=expression_names
        )

    def delete_problem(
        self,
        platform: str,
        problem_id: str
    ) -> bool:
        """
        Delete problem and all associated test cases (including S3 data)

        Args:
            platform: Platform name
            problem_id: Problem identifier

        Returns:
            True if deleted successfully
        """
        pk = f'PROB#{platform}#{problem_id}'

        # Get all items for this problem (META + test cases)
        items = self.query(
            key_condition_expression=Key('PK').eq(pk)
        )

        # Delete all items from DynamoDB
        success = True
        for item in items:
            if not self.delete_item(item['PK'], item['SK']):
                success = False

        # Delete S3 test cases
        try:
            self.s3_service.delete_testcases(platform, problem_id)
            logger.info(f"Deleted S3 test cases for {platform}/{problem_id}")
        except Exception as e:
            logger.error(f"Failed to delete S3 test cases: {e}")
            success = False

        return success

    def add_testcase(
        self,
        platform: str,
        problem_id: str,
        testcase_id: str,
        input_str: str,
        output_str: str
    ) -> Dict[str, Any]:
        """
        Add a test case to a problem and update test case count
        Automatically routes to S3 if test case is large (>=100KB)

        Args:
            platform: Platform name
            problem_id: Problem identifier
            testcase_id: Test case identifier (e.g., '1', '2', 'custom1')
            input_str: Test case input
            output_str: Expected output

        Returns:
            Created test case item
        """
        timestamp = self.get_timestamp()

        # Check if test case should be stored in S3
        use_s3 = self.s3_service.should_use_s3(input_str, output_str)

        if use_s3:
            # Store in S3 and save reference in DynamoDB
            try:
                s3_metadata = self.s3_service.store_testcase(
                    platform=platform,
                    problem_id=problem_id,
                    testcase_id=testcase_id,
                    input_str=input_str,
                    output_str=output_str
                )

                item = {
                    'PK': f'PROB#{platform}#{problem_id}',
                    'SK': f'TC#{testcase_id}',
                    'tp': 'tc',
                    'dat': {
                        's3_key': s3_metadata['s3_key'],
                        'size': s3_metadata['size'],
                        'compressed_size': s3_metadata['compressed_size'],
                        'storage': 's3'
                    },
                    'crt': timestamp
                }

                logger.info(
                    f"Stored large test case in S3: {platform}/{problem_id}/{testcase_id} "
                    f"({s3_metadata['size']} bytes)"
                )

            except Exception as e:
                logger.error(f"Failed to store test case in S3, falling back to DynamoDB: {e}")
                # Fallback to DynamoDB (will likely fail if too large, but try anyway)
                item = {
                    'PK': f'PROB#{platform}#{problem_id}',
                    'SK': f'TC#{testcase_id}',
                    'tp': 'tc',
                    'dat': {
                        'inp': input_str,
                        'out': output_str,
                        'storage': 'dynamodb'
                    },
                    'crt': timestamp
                }
        else:
            # Store directly in DynamoDB
            item = {
                'PK': f'PROB#{platform}#{problem_id}',
                'SK': f'TC#{testcase_id}',
                'tp': 'tc',
                'dat': {
                    'inp': input_str,
                    'out': output_str,
                    'storage': 'dynamodb'
                },
                'crt': timestamp
            }

        result = self.put_item(item)

        # Update test case count
        problem = self.get_problem(platform, problem_id)
        if problem:
            current_count = problem.get('test_case_count', 0)
            self.update_problem(
                platform=platform,
                problem_id=problem_id,
                updates={'test_case_count': current_count + 1}
            )

        return result

    def get_testcases(
        self,
        platform: str,
        problem_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all test cases for a problem (hybrid: DynamoDB + S3)

        Args:
            platform: Platform name
            problem_id: Problem identifier

        Returns:
            List of test case dictionaries with 'testcase_id', 'input', 'output'
        """
        pk = f'PROB#{platform}#{problem_id}'

        # Query DynamoDB for all test case items
        items = self.query(
            key_condition_expression=Key('PK').eq(pk) & Key('SK').begins_with('TC#')
        )

        test_cases = []

        for item in items:
            # Extract testcase_id from SK (e.g., "TC#1" -> "1")
            testcase_id = item['SK'].replace('TC#', '')
            storage_type = item['dat'].get('storage', 'dynamodb')

            try:
                if storage_type == 's3':
                    # Retrieve from S3 using s3_key
                    s3_key = item['dat'].get('s3_key')
                    if s3_key:
                        testcase_data = self.s3_service.retrieve_testcase(
                            platform=platform,
                            problem_id=problem_id,
                            testcase_id=testcase_id
                        )
                        if testcase_data:
                            test_cases.append({
                                'testcase_id': testcase_id,
                                'input': testcase_data['input'],
                                'output': testcase_data['output']
                            })
                    else:
                        logger.warning(f"Test case {testcase_id} marked as S3 but no s3_key found")
                else:
                    # Retrieve from DynamoDB
                    test_cases.append({
                        'testcase_id': testcase_id,
                        'input': item['dat'].get('inp', ''),
                        'output': item['dat'].get('out', '')
                    })
            except Exception as e:
                logger.error(f"Failed to retrieve test case {testcase_id}: {e}")
                continue

        # Sort by testcase_id (numeric sort if possible)
        try:
            test_cases.sort(key=lambda x: int(x['testcase_id']) if x['testcase_id'].isdigit() else x['testcase_id'])
        except:
            test_cases.sort(key=lambda x: x['testcase_id'])

        return test_cases

    def list_completed_problems(
        self,
        limit: int = 100,
        last_evaluated_key: Optional[Dict] = None
    ) -> tuple[List[Dict[str, Any]], Optional[Dict]]:
        """
        List completed problems using GSI3 (efficient Query operation)

        Args:
            limit: Maximum number of problems to return
            last_evaluated_key: Pagination cursor from previous request

        Returns:
            Tuple of (problems list, next_cursor)
        """
        query_params = {
            'IndexName': 'GSI3',
            'KeyConditionExpression': Key('GSI3PK').eq('PROB#COMPLETED'),
            'FilterExpression': Attr('dat.del').eq(False),
            'Limit': limit,
            'ScanIndexForward': False  # Newest first (descending by GSI3SK timestamp)
        }

        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key

        response = self.table.query(**query_params)
        items = response.get('Items', [])
        next_key = response.get('LastEvaluatedKey')

        problems = []
        for item in items:
            # Extract platform and problem_id from PK
            pk_parts = item['PK'].split('#')
            if len(pk_parts) >= 3:
                platform = pk_parts[1]
                problem_id = '#'.join(pk_parts[2:])  # Handle IDs with # in them

                problems.append({
                    'platform': platform,
                    'problem_id': problem_id,
                    'title': item['dat'].get('tit', ''),
                    'problem_url': item['dat'].get('url', ''),
                    'tags': item['dat'].get('tag', []),
                    'language': item['dat'].get('lng', ''),
                    'is_completed': item['dat'].get('cmp', False),
                    'test_case_count': item['dat'].get('tcc', 0),
                    'verified_by_admin': item['dat'].get('vrf', False),
                    'created_at': item.get('crt'),
                    'updated_at': item.get('upd')
                })

        return problems, next_key

    def list_draft_problems(
        self,
        limit: int = 100,
        last_evaluated_key: Optional[Dict] = None
    ) -> tuple[List[Dict[str, Any]], Optional[Dict]]:
        """
        List draft problems using GSI3 (efficient Query operation)

        Args:
            limit: Maximum number of problems to return
            last_evaluated_key: Pagination cursor from previous request

        Returns:
            Tuple of (problems list, next_cursor)
        """
        query_params = {
            'IndexName': 'GSI3',
            'KeyConditionExpression': Key('GSI3PK').eq('PROB#DRAFT'),
            'FilterExpression': Attr('dat.del').eq(False),
            'Limit': limit,
            'ScanIndexForward': False  # Newest first (descending by GSI3SK timestamp)
        }

        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key

        response = self.table.query(**query_params)
        items = response.get('Items', [])
        next_key = response.get('LastEvaluatedKey')

        problems = []
        for item in items:
            # Extract platform and problem_id from PK
            pk_parts = item['PK'].split('#')
            if len(pk_parts) >= 3:
                platform = pk_parts[1]
                problem_id = '#'.join(pk_parts[2:])

                problems.append({
                    'platform': platform,
                    'problem_id': problem_id,
                    'title': item['dat'].get('tit', ''),
                    'problem_url': item['dat'].get('url', ''),
                    'tags': item['dat'].get('tag', []),
                    'language': item['dat'].get('lng', ''),
                    'is_completed': item['dat'].get('cmp', False),
                    'test_case_count': item['dat'].get('tcc', 0),
                    'needs_review': item['dat'].get('nrv', False),
                    'created_at': item.get('crt'),
                    'updated_at': item.get('upd')
                })

        return problems, next_key

    def list_problems_needing_review(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List problems that need admin review (scan operation)

        Args:
            limit: Maximum number of problems to return

        Returns:
            List of problem dictionaries needing review
        """
        items = self.scan(
            filter_expression=Attr('tp').eq('prob') &
                            Attr('dat.nrv').eq(True) &
                            Attr('dat.del').eq(False) &
                            Attr('SK').eq('META'),
            limit=limit
        )

        problems = []
        for item in items:
            pk_parts = item['PK'].split('#')
            if len(pk_parts) >= 3:
                platform = pk_parts[1]
                problem_id = '#'.join(pk_parts[2:])

                problems.append({
                    'platform': platform,
                    'problem_id': problem_id,
                    'title': item['dat'].get('tit', ''),
                    'problem_url': item['dat'].get('url', ''),
                    'tags': item['dat'].get('tag', []),
                    'language': item['dat'].get('lng', ''),
                    'needs_review': item['dat'].get('nrv', False),
                    'review_notes': item['dat'].get('rvn'),
                    'verified_by_admin': item['dat'].get('vrf', False),
                    'created_at': item.get('crt'),
                    'updated_at': item.get('upd')
                })

        # Sort by created_at ascending (oldest first)
        problems.sort(key=lambda x: x.get('created_at', 0))
        return problems

    def soft_delete_problem(
        self,
        platform: str,
        problem_id: str,
        reason: str = ''
    ) -> Dict[str, Any]:
        """
        Soft delete a problem by marking it as deleted

        Args:
            platform: Platform name
            problem_id: Problem identifier
            reason: Reason for deletion

        Returns:
            Updated problem item
        """
        timestamp = self.get_timestamp()

        return self.update_problem(
            platform=platform,
            problem_id=problem_id,
            updates={
                'is_deleted': True,
                'deleted_at': timestamp,
                'deleted_reason': reason
            }
        )
