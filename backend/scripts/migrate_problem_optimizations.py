#!/usr/bin/env python3
"""
Migration script for Problem optimization updates:
1. Add test_case_count (tcc) to all existing problems
2. Add GSI3PK and GSI3SK for problem status indexing

This script should be run once after deploying the optimization changes.
"""
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from api.dynamodb.client import DynamoDBClient
from boto3.dynamodb.conditions import Key, Attr


def migrate_problems():
    """Migrate all existing problems to add test_case_count and GSI3 attributes"""

    print("=" * 70)
    print("Problem Optimization Migration")
    print("=" * 70)
    print()

    table = DynamoDBClient.get_table()

    # Scan for all problem metadata items
    print("Step 1: Scanning for all problems...")
    scan_params = {
        'FilterExpression': Attr('tp').eq('prob') & Attr('SK').eq('META')
    }

    problems = []
    last_evaluated_key = None

    while True:
        if last_evaluated_key:
            scan_params['ExclusiveStartKey'] = last_evaluated_key

        response = table.scan(**scan_params)
        problems.extend(response.get('Items', []))

        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

    print(f"✓ Found {len(problems)} problems to migrate")
    print()

    # Process each problem
    print("Step 2: Updating problems with test_case_count and GSI3 attributes...")
    updated_count = 0
    skipped_count = 0
    error_count = 0

    for i, problem in enumerate(problems, 1):
        pk = problem['PK']
        sk = problem['SK']

        # Extract platform and problem_id for logging
        pk_parts = pk.split('#')
        if len(pk_parts) >= 3:
            platform = pk_parts[1]
            problem_id = '#'.join(pk_parts[2:])
        else:
            platform = 'unknown'
            problem_id = 'unknown'

        try:
            # Check if already migrated
            if 'GSI3PK' in problem and 'tcc' in problem.get('dat', {}):
                print(f"  [{i}/{len(problems)}] Skipped: {platform}#{problem_id} (already migrated)")
                skipped_count += 1
                continue

            # Count test cases for this problem
            tc_response = table.query(
                KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('TC#')
            )
            test_case_count = len(tc_response.get('Items', []))

            # Determine GSI3PK based on completion status
            is_completed = problem.get('dat', {}).get('cmp', False)
            gsi3pk = 'PROB#COMPLETED' if is_completed else 'PROB#DRAFT'

            # Use existing updated timestamp or current timestamp
            gsi3sk = problem.get('upd', problem.get('crt', int(datetime.now().timestamp())))

            # Update the problem
            update_expression = 'SET dat.#tcc = :tcc, #gsi3pk = :gsi3pk, #gsi3sk = :gsi3sk'
            expression_names = {
                '#tcc': 'tcc',
                '#gsi3pk': 'GSI3PK',
                '#gsi3sk': 'GSI3SK'
            }
            expression_values = {
                ':tcc': test_case_count,
                ':gsi3pk': gsi3pk,
                ':gsi3sk': gsi3sk
            }

            table.update_item(
                Key={'PK': pk, 'SK': sk},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values
            )

            print(f"  [{i}/{len(problems)}] Updated: {platform}#{problem_id} "
                  f"(test_cases={test_case_count}, status={gsi3pk})")
            updated_count += 1

        except Exception as e:
            print(f"  [{i}/{len(problems)}] ERROR: {platform}#{problem_id}: {e}")
            error_count += 1

    print()
    print("=" * 70)
    print("Migration Summary")
    print("=" * 70)
    print(f"Total problems found:  {len(problems)}")
    print(f"Successfully updated:  {updated_count}")
    print(f"Already migrated:      {skipped_count}")
    print(f"Errors:                {error_count}")
    print("=" * 70)

    if error_count > 0:
        print("\n⚠️  Some problems failed to migrate. Please review the errors above.")
        sys.exit(1)
    else:
        print("\n✅ Migration completed successfully!")


if __name__ == '__main__':
    try:
        migrate_problems()
    except KeyboardInterrupt:
        print("\n\n❌ Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
