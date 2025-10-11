#!/usr/bin/env python3
"""
Plan Structure Migration Script for LocalStack

This script migrates plan structure in LocalStack environment.

Safety features:
- Dry-run mode by default
- Backup creation
- Rollback capability
- Verification at each step

Usage:
  # Dry run (safe, no changes)
  python migrate_plan_structure_production.py --dry-run

  # Actual migration (requires confirmation)
  python migrate_plan_structure_production.py --execute

  # Rollback to old structure
  python migrate_plan_structure_production.py --rollback
"""
import os
import sys
import django
import asyncio
import argparse
import json
from datetime import datetime

# Add backend to path
sys.path.insert(0, '/Users/gwonsoolee/algoitny/backend')

# Setup Django for LocalStack (development/testing)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('ENVIRONMENT', 'development')
os.environ.setdefault('AWS_DEFAULT_REGION', 'ap-northeast-2')
# Use LocalStack URL for local testing
os.environ.setdefault('LOCALSTACK_URL', 'http://localhost:4566')
django.setup()

from api.dynamodb.async_client import AsyncDynamoDBClient


class PlanMigration:
    """Safe plan migration with rollback support (LocalStack)"""

    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.backup_file = f"plan_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.migration_log = []

    def log(self, message, level="INFO"):
        """Log migration progress"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        self.migration_log.append(log_entry)

    async def backup_plans(self, table):
        """Backup existing plans to JSON file"""
        self.log("Creating backup of existing plans...", "INFO")

        response = await table.scan(
            FilterExpression='#tp = :tp AND SK = :sk',
            ExpressionAttributeNames={'#tp': 'tp'},
            ExpressionAttributeValues={':tp': 'plan', ':sk': 'META'}
        )

        old_plans = response.get('Items', [])

        # Convert Decimal to int/float for JSON serialization
        def decimal_default(obj):
            from decimal import Decimal
            if isinstance(obj, Decimal):
                return int(obj) if obj % 1 == 0 else float(obj)
            raise TypeError

        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'table_name': AsyncDynamoDBClient._table_name,
            'plan_count': len(old_plans),
            'plans': old_plans
        }

        backup_path = f"/Users/gwonsoolee/algoitny/backend/scripts/backups/{self.backup_file}"
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2, default=decimal_default)

        self.log(f"✓ Backup saved: {backup_path}", "SUCCESS")
        self.log(f"  Backed up {len(old_plans)} plans", "INFO")

        return old_plans, backup_path

    async def verify_old_structure(self, table):
        """Verify old structure exists"""
        self.log("Verifying old structure...", "INFO")

        response = await table.scan(
            FilterExpression='#tp = :tp AND SK = :sk',
            ExpressionAttributeNames={'#tp': 'tp'},
            ExpressionAttributeValues={':tp': 'plan', ':sk': 'META'}
        )

        old_plans = response.get('Items', [])

        if not old_plans:
            self.log("No plans found with old structure", "WARNING")
            return False

        self.log(f"✓ Found {len(old_plans)} plans with old structure", "SUCCESS")
        for item in old_plans:
            plan_name = item.get('dat', {}).get('nm', 'Unknown')
            self.log(f"  - {item['PK']}: {plan_name}", "INFO")

        return True

    async def verify_new_structure(self, table):
        """Verify new structure doesn't exist yet"""
        self.log("Checking if new structure already exists...", "INFO")

        response = await table.query(
            KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
            ExpressionAttributeValues={':pk': 'PLAN', ':sk': 'META#'}
        )

        new_plans = response.get('Items', [])

        if new_plans:
            self.log(f"⚠ WARNING: Found {len(new_plans)} plans with new structure", "WARNING")
            self.log("  Migration may have already been run!", "WARNING")
            return True

        self.log("✓ New structure doesn't exist yet", "SUCCESS")
        return False

    async def migrate_to_new_structure(self, table, old_plans):
        """Migrate plans to new structure"""
        self.log("=" * 70, "INFO")
        self.log("Starting migration to new structure...", "INFO")
        self.log("=" * 70, "INFO")

        if self.dry_run:
            self.log("DRY RUN MODE - No changes will be made", "WARNING")

        migrated_count = 0

        for item in old_plans:
            old_pk = item['PK']
            plan_id = old_pk.replace('PLAN#', '')
            plan_name = item.get('dat', {}).get('nm', 'Unknown')

            self.log(f"Migrating Plan #{plan_id}: {plan_name}", "INFO")
            self.log(f"  Old: PK={old_pk}, SK=META", "INFO")
            self.log(f"  New: PK=PLAN, SK=META#{plan_id}", "INFO")

            if not self.dry_run:
                # Create new item
                new_item = item.copy()
                new_item['PK'] = 'PLAN'
                new_item['SK'] = f'META#{plan_id}'
                await table.put_item(Item=new_item)
                self.log(f"  ✓ Created new structure item", "SUCCESS")
                migrated_count += 1
            else:
                self.log(f"  [DRY RUN] Would create new structure item", "INFO")

        return migrated_count

    async def delete_old_structure(self, table, old_plans):
        """Delete old structure items"""
        self.log("=" * 70, "INFO")
        self.log("Deleting old structure items...", "INFO")
        self.log("=" * 70, "INFO")

        deleted_count = 0

        for item in old_plans:
            old_pk = item['PK']
            plan_id = old_pk.replace('PLAN#', '')

            self.log(f"Deleting old item: PK={old_pk}, SK=META", "INFO")

            if not self.dry_run:
                await table.delete_item(Key={'PK': old_pk, 'SK': 'META'})
                self.log(f"  ✓ Deleted", "SUCCESS")
                deleted_count += 1
            else:
                self.log(f"  [DRY RUN] Would delete old item", "INFO")

        return deleted_count

    async def verify_migration(self, table):
        """Verify migration was successful"""
        self.log("=" * 70, "INFO")
        self.log("Verifying migration...", "INFO")
        self.log("=" * 70, "INFO")

        # Check no old items remain
        response = await table.scan(
            FilterExpression='#tp = :tp AND SK = :sk AND begins_with(PK, :pk)',
            ExpressionAttributeNames={'#tp': 'tp'},
            ExpressionAttributeValues={':tp': 'plan', ':sk': 'META', ':pk': 'PLAN#'}
        )

        remaining_old = response.get('Items', [])
        if remaining_old:
            self.log(f"✗ FAILED: {len(remaining_old)} old items still exist!", "ERROR")
            return False

        self.log("✓ No old structure items remain", "SUCCESS")

        # Verify new items
        response = await table.query(
            KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
            ExpressionAttributeValues={':pk': 'PLAN', ':sk': 'META#'}
        )

        new_plans = response.get('Items', [])
        self.log(f"✓ Found {len(new_plans)} plans with new structure", "SUCCESS")

        for item in sorted(new_plans, key=lambda x: x['SK']):
            plan_name = item.get('dat', {}).get('nm', 'Unknown')
            self.log(f"  - {item['SK']}: {plan_name}", "INFO")

        return True

    async def rollback_migration(self, backup_path):
        """Rollback migration using backup file"""
        self.log("=" * 70, "INFO")
        self.log("Starting ROLLBACK...", "WARNING")
        self.log("=" * 70, "INFO")

        if not os.path.exists(backup_path):
            self.log(f"✗ Backup file not found: {backup_path}", "ERROR")
            return False

        with open(backup_path, 'r') as f:
            backup_data = json.load(f)

        old_plans = backup_data['plans']
        self.log(f"Loaded {len(old_plans)} plans from backup", "INFO")

        async with AsyncDynamoDBClient.get_resource() as resource:
            table = await resource.Table(AsyncDynamoDBClient._table_name)

            # Delete new structure items
            self.log("Deleting new structure items...", "INFO")
            response = await table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={':pk': 'PLAN', ':sk': 'META#'}
            )

            for item in response.get('Items', []):
                if not self.dry_run:
                    await table.delete_item(Key={'PK': item['PK'], 'SK': item['SK']})
                    self.log(f"  Deleted {item['SK']}", "INFO")

            # Restore old structure
            self.log("Restoring old structure...", "INFO")
            for item in old_plans:
                if not self.dry_run:
                    await table.put_item(Item=item)
                    self.log(f"  Restored {item['PK']}", "INFO")

        self.log("✓ Rollback completed", "SUCCESS")
        return True

    async def run_migration(self):
        """Execute the full migration process"""
        self.log("=" * 70, "INFO")
        self.log("PLAN STRUCTURE MIGRATION (LocalStack)", "INFO")
        self.log("=" * 70, "INFO")
        self.log(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}", "WARNING")
        self.log(f"Table: {AsyncDynamoDBClient._table_name}", "INFO")
        self.log(f"LocalStack URL: {os.environ.get('LOCALSTACK_URL', 'Not set')}", "INFO")
        self.log("=" * 70, "INFO")

        if not self.dry_run:
            confirm = input("\n⚠ WARNING: This will modify LocalStack data!\nType 'MIGRATE' to continue: ")
            if confirm != 'MIGRATE':
                self.log("Migration cancelled by user", "INFO")
                return False

        async with AsyncDynamoDBClient.get_resource() as resource:
            table = await resource.Table(AsyncDynamoDBClient._table_name)

            # Step 1: Verify old structure exists
            if not await self.verify_old_structure(table):
                self.log("✗ Migration aborted: No old structure found", "ERROR")
                return False

            # Step 2: Check if new structure already exists
            if await self.verify_new_structure(table):
                self.log("⚠ Migration may have already been run", "WARNING")
                if not self.dry_run:
                    confirm = input("Continue anyway? (yes/no): ")
                    if confirm.lower() != 'yes':
                        return False

            # Step 3: Backup
            old_plans, backup_path = await self.backup_plans(table)
            self.log(f"Backup location: {backup_path}", "INFO")

            # Step 4: Migrate to new structure
            migrated = await self.migrate_to_new_structure(table, old_plans)
            if not self.dry_run:
                self.log(f"✓ Migrated {migrated} plans", "SUCCESS")

            # Step 5: Delete old structure
            deleted = await self.delete_old_structure(table, old_plans)
            if not self.dry_run:
                self.log(f"✓ Deleted {deleted} old items", "SUCCESS")

            # Step 6: Verify
            if not self.dry_run:
                if not await self.verify_migration(table):
                    self.log("✗ Migration verification FAILED!", "ERROR")
                    self.log(f"Use backup to rollback: {backup_path}", "WARNING")
                    return False

        self.log("=" * 70, "INFO")
        if self.dry_run:
            self.log("✓ DRY RUN completed successfully", "SUCCESS")
            self.log("Run with --execute to perform actual migration", "INFO")
        else:
            self.log("✓ MIGRATION completed successfully!", "SUCCESS")
            self.log(f"Backup saved at: {backup_path}", "INFO")
        self.log("=" * 70, "INFO")

        return True


async def main():
    parser = argparse.ArgumentParser(description='Plan Structure Migration (LocalStack)')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Dry run mode (default, no changes)')
    parser.add_argument('--execute', action='store_true',
                        help='Execute actual migration')
    parser.add_argument('--rollback', type=str, metavar='BACKUP_FILE',
                        help='Rollback using backup file')

    args = parser.parse_args()

    dry_run = not args.execute
    migration = PlanMigration(dry_run=dry_run)

    if args.rollback:
        await migration.rollback_migration(args.rollback)
    else:
        await migration.run_migration()


if __name__ == '__main__':
    asyncio.run(main())
