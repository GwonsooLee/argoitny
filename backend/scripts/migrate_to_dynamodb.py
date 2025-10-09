#!/usr/bin/env python3
"""
Migrate data from MySQL to DynamoDB

This script migrates all data from Django ORM (MySQL) to DynamoDB
using the repository pattern.

Usage:
    python scripts/migrate_to_dynamodb.py [--entity ENTITY] [--batch-size SIZE] [--dry-run]

Options:
    --entity ENTITY      Migrate only specific entity (user, problem, history, etc.)
    --batch-size SIZE    Number of items per batch (default: 25)
    --dry-run            Show what would be migrated without actually migrating
"""
import os
import sys
import argparse
import django
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from api.models import (
    User, SubscriptionPlan, Problem, TestCase, SearchHistory,
    UsageLog, ScriptGenerationJob, ProblemExtractionJob
)
from api.dynamodb.client import DynamoDBClient
from api.dynamodb.repositories import (
    UserRepository, ProblemRepository, SearchHistoryRepository, UsageLogRepository
)


class MigrationStats:
    """Track migration statistics"""
    def __init__(self):
        self.stats = {}

    def add(self, entity, count):
        if entity not in self.stats:
            self.stats[entity] = 0
        self.stats[entity] += count

    def print_summary(self):
        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)
        for entity, count in self.stats.items():
            print(f"{entity:25s}: {count:6d} items")
        print("=" * 60)


def migrate_users(repo, batch_size=25, dry_run=False):
    """Migrate users from MySQL to DynamoDB"""
    print("\nMigrating Users...")
    users = User.objects.all()
    total = users.count()
    print(f"Found {total} users")

    if dry_run:
        print("DRY RUN: Would migrate users")
        return total

    migrated = 0
    batch = []

    for user in users.iterator(chunk_size=batch_size):
        user_data = {
            'user_id': user.id,
            'email': user.email,
            'name': user.name or '',
            'picture': user.picture or '',
            'google_id': user.google_id or '',
            'subscription_plan_id': user.subscription_plan_id,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
        }

        batch.append(user_data)

        if len(batch) >= batch_size:
            repo.batch_create_users(batch)
            migrated += len(batch)
            print(f"  Migrated {migrated}/{total} users...", end='\r')
            batch = []

    # Migrate remaining
    if batch:
        repo.batch_create_users(batch)
        migrated += len(batch)

    print(f"  Migrated {migrated}/{total} users... Done!")
    return migrated


def migrate_problems(repo, batch_size=25, dry_run=False):
    """Migrate problems and test cases from MySQL to DynamoDB"""
    print("\nMigrating Problems...")
    problems = Problem.objects.prefetch_related('test_cases').all()
    total = problems.count()
    print(f"Found {total} problems")

    if dry_run:
        print("DRY RUN: Would migrate problems")
        return total

    migrated = 0
    testcases_migrated = 0

    for problem in problems.iterator(chunk_size=batch_size):
        # Migrate problem
        problem_data = {
            'title': problem.title,
            'problem_url': problem.problem_url or '',
            'tags': problem.tags or [],
            'solution_code': problem.solution_code or '',
            'language': problem.language or '',
            'constraints': problem.constraints or '',
            'is_completed': problem.is_completed,
            'is_deleted': problem.is_deleted,
            'deleted_at': int(problem.deleted_at.timestamp()) if problem.deleted_at else None,
            'deleted_reason': problem.deleted_reason or '',
            'needs_review': problem.needs_review,
            'review_notes': problem.review_notes or '',
            'verified_by_admin': problem.verified_by_admin,
            'reviewed_at': int(problem.reviewed_at.timestamp()) if problem.reviewed_at else None,
            'metadata': problem.metadata or {},
        }

        repo.create_problem(problem.platform, problem.problem_id, problem_data)
        migrated += 1

        # Migrate test cases
        for idx, tc in enumerate(problem.test_cases.all(), start=1):
            repo.add_testcase(
                problem.platform,
                problem.problem_id,
                str(idx),
                tc.input,
                tc.output
            )
            testcases_migrated += 1

        print(f"  Migrated {migrated}/{total} problems ({testcases_migrated} test cases)...", end='\r')

    print(f"  Migrated {migrated}/{total} problems ({testcases_migrated} test cases)... Done!")
    return migrated


def migrate_search_history(repo, batch_size=25, dry_run=False):
    """Migrate search history from MySQL to DynamoDB"""
    print("\nMigrating Search History...")
    histories = SearchHistory.objects.all()
    total = histories.count()
    print(f"Found {total} history items")

    if dry_run:
        print("DRY RUN: Would migrate search history")
        return total

    migrated = 0

    for history in histories.iterator(chunk_size=batch_size):
        history_data = {
            'uid': history.user_id,
            'uidt': history.user_identifier,
            'pid': history.problem_id,
            'plt': history.platform,
            'pno': history.problem_number,
            'ptt': history.problem_title,
            'lng': history.language,
            'cod': history.code,
            'res': history.result_summary,
            'psc': history.passed_count,
            'fsc': history.failed_count,
            'toc': history.total_count,
            'pub': history.is_code_public,
            'trs': history.test_results,
            'hnt': history.hints,
            'met': history.metadata or {},
        }

        repo.create_history(history.id, history_data)
        migrated += 1
        print(f"  Migrated {migrated}/{total} history items...", end='\r')

    print(f"  Migrated {migrated}/{total} history items... Done!")
    return migrated


def migrate_usage_logs(repo, batch_size=100, dry_run=False):
    """Migrate usage logs from MySQL to DynamoDB"""
    print("\nMigrating Usage Logs...")
    logs = UsageLog.objects.all()
    total = logs.count()
    print(f"Found {total} usage logs")

    if dry_run:
        print("DRY RUN: Would migrate usage logs")
        return total

    migrated = 0

    for log in logs.iterator(chunk_size=batch_size):
        repo.log_usage(
            user_id=log.user_id,
            action=log.action,
            problem_id=log.problem_id,
            metadata=log.metadata or {},
            timestamp=int(log.created_at.timestamp())
        )
        migrated += 1
        print(f"  Migrated {migrated}/{total} usage logs...", end='\r')

    print(f"  Migrated {migrated}/{total} usage logs... Done!")
    return migrated


def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description='Migrate MySQL data to DynamoDB')
    parser.add_argument('--entity', choices=['user', 'problem', 'history', 'usage', 'all'],
                        default='all', help='Entity to migrate')
    parser.add_argument('--batch-size', type=int, default=25, help='Batch size for migration')
    parser.add_argument('--dry-run', action='store_true', help='Dry run without actual migration')

    args = parser.parse_args()

    print("=" * 60)
    print("MySQL to DynamoDB Migration")
    print("=" * 60)
    print(f"Entity: {args.entity}")
    print(f"Batch Size: {args.batch_size}")
    print(f"Dry Run: {args.dry_run}")
    print("=" * 60)

    # Initialize repositories
    table = DynamoDBClient.get_table()
    user_repo = UserRepository(table)
    problem_repo = ProblemRepository(table)
    history_repo = SearchHistoryRepository(table)
    usage_repo = UsageLogRepository(table)

    stats = MigrationStats()

    # Run migrations
    try:
        if args.entity in ['user', 'all']:
            count = migrate_users(user_repo, args.batch_size, args.dry_run)
            stats.add('Users', count)

        if args.entity in ['problem', 'all']:
            count = migrate_problems(problem_repo, args.batch_size, args.dry_run)
            stats.add('Problems', count)

        if args.entity in ['history', 'all']:
            count = migrate_search_history(history_repo, args.batch_size, args.dry_run)
            stats.add('Search History', count)

        if args.entity in ['usage', 'all']:
            count = migrate_usage_logs(usage_repo, args.batch_size, args.dry_run)
            stats.add('Usage Logs', count)

        stats.print_summary()

        if args.dry_run:
            print("\n✓ DRY RUN COMPLETE - No data was migrated")
        else:
            print("\n✓ MIGRATION COMPLETE")

    except Exception as e:
        print(f"\n✗ MIGRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
