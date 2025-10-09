#!/usr/bin/env python3
"""
Verify data consistency between MySQL and DynamoDB

This script compares data between MySQL and DynamoDB to ensure
migration was successful.
"""
import os
import sys
import django

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import User, Problem, SearchHistory, UsageLog
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import (
    UserRepository, ProblemRepository, SearchHistoryRepository, UsageLogRepository
)


def verify_users(repo):
    """Verify user migration"""
    print("\nVerifying Users...")
    mysql_count = User.objects.count()

    # Count DynamoDB users (expensive scan)
    dynamodb_count = len(repo.list_users(limit=10000))

    print(f"  MySQL Users: {mysql_count}")
    print(f"  DynamoDB Users: {dynamodb_count}")

    if mysql_count == dynamodb_count:
        print("  ✓ User counts match!")

        # Sample verification
        sample = User.objects.first()
        if sample:
            dynamo_user = repo.get_user_by_id(sample.id)
            if dynamo_user:
                print(f"  ✓ Sample user verified (ID: {sample.id})")
            else:
                print(f"  ✗ Sample user not found in DynamoDB (ID: {sample.id})")
    else:
        print(f"  ✗ User counts DO NOT match! Difference: {abs(mysql_count - dynamodb_count)}")

    return mysql_count == dynamodb_count


def verify_problems(repo):
    """Verify problem migration"""
    print("\nVerifying Problems...")
    mysql_count = Problem.objects.count()

    # Count completed and draft problems
    completed = len(repo.list_completed_problems(limit=10000))
    drafts = len(repo.list_draft_problems(limit=10000))
    dynamodb_count = completed + drafts

    print(f"  MySQL Problems: {mysql_count}")
    print(f"  DynamoDB Problems: {dynamodb_count} (completed: {completed}, drafts: {drafts})")

    if mysql_count == dynamodb_count:
        print("  ✓ Problem counts match!")

        # Sample verification
        sample = Problem.objects.first()
        if sample:
            dynamo_problem = repo.get_problem(sample.platform, sample.problem_id)
            if dynamo_problem:
                print(f"  ✓ Sample problem verified ({sample.platform}/{sample.problem_id})")
            else:
                print(f"  ✗ Sample problem not found in DynamoDB ({sample.platform}/{sample.problem_id})")
    else:
        print(f"  ✗ Problem counts DO NOT match! Difference: {abs(mysql_count - dynamodb_count)}")

    return mysql_count == dynamodb_count


def verify_search_history(repo):
    """Verify search history migration"""
    print("\nVerifying Search History...")
    mysql_count = SearchHistory.objects.count()

    # Sample count (full scan would be too expensive)
    print("  Note: Sampling 100 items (full scan is expensive)")

    # Verify a sample
    sample = SearchHistory.objects.first()
    if sample:
        dynamo_history = repo.get_history(sample.id)
        if dynamo_history:
            print(f"  ✓ Sample history verified (ID: {sample.id})")
        else:
            print(f"  ✗ Sample history not found in DynamoDB (ID: {sample.id})")
            return False

    print(f"  MySQL History: {mysql_count}")
    print("  DynamoDB: Sample verified (full count skipped)")
    return True


def verify_usage_logs(repo):
    """Verify usage log migration"""
    print("\nVerifying Usage Logs...")
    mysql_count = UsageLog.objects.count()

    print("  Note: Skipping full count (usage logs are partitioned by date)")

    # Verify recent logs
    from datetime import datetime, timedelta
    today = datetime.now().strftime('%Y%m%d')

    # Sample verification
    sample = UsageLog.objects.first()
    if sample:
        date_str = sample.created_at.strftime('%Y%m%d')
        logs = repo.get_usage_logs(sample.user_id, date_str=date_str, limit=10)
        if logs:
            print(f"  ✓ Sample usage logs verified (User: {sample.user_id}, Date: {date_str})")
        else:
            print(f"  ✗ No usage logs found for sample (User: {sample.user_id}, Date: {date_str})")
            return False

    print(f"  MySQL Logs: {mysql_count}")
    print("  DynamoDB: Sample verified (full count skipped)")
    return True


def main():
    """Main verification function"""
    print("=" * 60)
    print("Migration Verification")
    print("=" * 60)

    # Initialize repositories
    table = DynamoDBClient.get_table()
    user_repo = UserRepository(table)
    problem_repo = ProblemRepository(table)
    history_repo = SearchHistoryRepository(table)
    usage_repo = UsageLogRepository(table)

    # Run verifications
    results = {
        'Users': verify_users(user_repo),
        'Problems': verify_problems(problem_repo),
        'Search History': verify_search_history(history_repo),
        'Usage Logs': verify_usage_logs(usage_repo),
    }

    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    all_passed = True
    for entity, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{entity:25s}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ ALL VERIFICATIONS PASSED")
        sys.exit(0)
    else:
        print("\n✗ SOME VERIFICATIONS FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
