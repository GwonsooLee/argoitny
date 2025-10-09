"""SearchHistory repository for DynamoDB operations"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from .base_repository import BaseRepository


class SearchHistoryRepository(BaseRepository):
    """
    Repository for SearchHistory entity

    Entity Pattern:
    - PK: EMAIL#{email}#SHIST#{platform}#{problem_number}
    - SK: HIST#{timestamp}
    - GSI1PK: PUBLIC#HIST
    - GSI1SK: {timestamp} (only if is_code_public=True)
    - tp: shist
    - dat: {
        'plat': platform,
        'pnum': problem_number,
        'ptitle': problem_title,
        'code': user_code (optional),
        'pub': is_code_public (boolean),
        'hints': hints (optional list)
    }
    - crt: created_at timestamp

    Example item:
    {
        'PK': 'EMAIL#user@example.com#SHIST#baekjoon#1000',
        'SK': 'HIST#1759912800000',
        'GSI1PK': 'PUBLIC#HIST',
        'GSI1SK': '1759912800000',
        'tp': 'shist',
        'dat': {
            'plat': 'baekjoon',
            'pnum': '1000',
            'ptitle': 'A+B',
            'code': 'print(sum(map(int, input().split())))',
            'pub': True,
            'hints': ['힌트1', '힌트2']
        },
        'crt': 1759912800000
    }
    """

    def __init__(self, table=None):
        if table is None:
            from ..client import DynamoDBClient
            table = DynamoDBClient.get_table()
        super().__init__(table)

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
        Create a new search history entry

        Args:
            email: User email
            platform: Platform name (e.g., 'baekjoon', 'codeforces')
            problem_number: Problem number
            problem_title: Problem title
            code: User's code (optional)
            is_code_public: Whether code is public
            hints: List of hints (optional)

        Returns:
            Created search history dict
        """
        import time
        timestamp = int(time.time() * 1000)

        dat = {
            'plat': platform,
            'pnum': problem_number,
            'ptitle': problem_title,
            'pub': is_code_public
        }

        if code:
            dat['code'] = code
        if hints:
            dat['hints'] = hints

        item = {
            'PK': f'EMAIL#{email}#SHIST#{platform}#{problem_number}',
            'SK': f'HIST#{timestamp}',
            'tp': 'shist',
            'dat': dat,
            'crt': Decimal(str(timestamp))
        }

        # Add to public GSI if code is public
        if is_code_public:
            item['GSI1PK'] = 'PUBLIC#HIST'
            item['GSI1SK'] = str(timestamp)

        self.put_item(item)

        return self._transform_to_long_format(item)

    def get_user_search_history(
        self,
        email: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all search history for a user

        Args:
            email: User email
            limit: Maximum number of items to return

        Returns:
            List of search history dicts (newest first)
        """
        # Query all items starting with EMAIL#{email}#SHIST#
        key_condition = Key('PK').begins_with(f'EMAIL#{email}#SHIST#') & Key('SK').begins_with('HIST#')

        items = self.query(
            key_condition_expression=key_condition,
            limit=limit,
            scan_index_forward=False  # Descending order (newest first)
        )

        return [self._transform_to_long_format(item) for item in items]

    def get_user_problem_history(
        self,
        email: str,
        platform: str,
        problem_number: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get search history for a specific problem

        Args:
            email: User email
            platform: Platform name
            problem_number: Problem number
            limit: Maximum number of items

        Returns:
            List of search history dicts for this problem (newest first)
        """
        pk = f'EMAIL#{email}#SHIST#{platform}#{problem_number}'

        items = self.query(
            key_condition_expression=Key('PK').eq(pk) & Key('SK').begins_with('HIST#'),
            limit=limit,
            scan_index_forward=False
        )

        return [self._transform_to_long_format(item) for item in items]

    def count_unique_problems(self, email: str) -> int:
        """
        Count unique problems tested by user

        Args:
            email: User email

        Returns:
            Count of unique problems
        """
        # Query all search history items
        items = self.query(
            key_condition_expression=Key('PK').begins_with(f'EMAIL#{email}#SHIST#')
        )

        # Extract unique platform#problem_number combinations from PK
        unique_problems = set()
        for item in items:
            pk = item.get('PK', '')
            # PK format: EMAIL#{email}#SHIST#{platform}#{problem_number}
            parts = pk.split('#')
            if len(parts) >= 5:
                platform = parts[3]
                problem_number = parts[4]
                unique_problems.add(f'{platform}#{problem_number}')

        return len(unique_problems)

    def get_public_history(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get public search history (for public feed)

        Args:
            limit: Maximum number of items

        Returns:
            List of public search history dicts (newest first)
        """
        items = self.query(
            index_name='GSI1',
            key_condition_expression=Key('GSI1PK').eq('PUBLIC#HIST'),
            limit=limit,
            scan_index_forward=False
        )

        return [self._transform_to_long_format(item) for item in items]

    def update_hints(
        self,
        email: str,
        platform: str,
        problem_number: str,
        timestamp: int,
        hints: List[str]
    ) -> bool:
        """
        Update hints for a search history entry

        Args:
            email: User email
            platform: Platform name
            problem_number: Problem number
            timestamp: Timestamp of the history entry
            hints: New hints list

        Returns:
            True if updated successfully
        """
        pk = f'EMAIL#{email}#SHIST#{platform}#{problem_number}'
        sk = f'HIST#{timestamp}'

        try:
            self.table.update_item(
                Key={'PK': pk, 'SK': sk},
                UpdateExpression='SET dat.hints = :hints',
                ExpressionAttributeValues={':hints': hints}
            )
            return True
        except Exception:
            return False

    def _transform_to_long_format(self, item: Dict) -> Dict:
        """Transform DynamoDB item to readable format"""
        dat = item.get('dat', {})

        # Extract email from PK
        pk = item.get('PK', '')
        email = pk.split('#')[1] if len(pk.split('#')) > 1 else ''

        # Extract timestamp from SK
        sk = item.get('SK', '')
        timestamp = int(sk.split('#')[1]) if len(sk.split('#')) > 1 else 0

        return {
            'email': email,
            'platform': dat.get('plat', ''),
            'problem_number': dat.get('pnum', ''),
            'problem_title': dat.get('ptitle', ''),
            'code': dat.get('code'),
            'is_code_public': dat.get('pub', False),
            'hints': dat.get('hints', []),
            'created_at': timestamp
        }
