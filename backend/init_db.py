#!/usr/bin/env python3
"""
DynamoDB initialization script

This script:
1. Initializes DynamoDB table
2. Seeds default subscription plans to DynamoDB

Note: MySQL has been removed. This project now uses DynamoDB exclusively.
SQLite is used only as a dummy database for Django's internal requirements.
"""
import os
import sys
import subprocess
import time

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_command(command, description):
    """
    Run a shell command and handle errors

    Args:
        command: Command to run (list or string)
        description: Description of what the command does

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'=' * 60}")
    print(f"{description}")
    print(f"{'=' * 60}")

    try:
        if isinstance(command, str):
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=False,
                text=True
            )
        else:
            result = subprocess.run(
                command,
                check=True,
                capture_output=False,
                text=True
            )

        print(f"✅ {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"❌ {description} - Failed")
        print(f"Error: {e}")
        return False


def wait_for_localstack(max_retries=30, delay=2):
    """
    Wait for LocalStack to be ready

    Args:
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds

    Returns:
        True if LocalStack is ready, False otherwise
    """
    print(f"\n{'=' * 60}")
    print("Waiting for LocalStack to be ready...")
    print(f"{'=' * 60}")

    localstack_url = os.getenv('LOCALSTACK_URL', 'http://localstack:4566')

    for i in range(max_retries):
        try:
            import requests
            response = requests.get(f"{localstack_url}/_localstack/health", timeout=2)

            if response.status_code == 200:
                health_data = response.json()
                dynamodb_status = health_data.get('services', {}).get('dynamodb', 'unavailable')

                if dynamodb_status in ['available', 'running']:
                    print(f"✅ LocalStack DynamoDB is ready!")
                    return True
                else:
                    print(f"⏳ Attempt {i+1}/{max_retries}: DynamoDB status: {dynamodb_status}")
            else:
                print(f"⏳ Attempt {i+1}/{max_retries}: Health check returned {response.status_code}")
        except Exception as e:
            print(f"⏳ Attempt {i+1}/{max_retries}: LocalStack not ready yet... ({e})")

        time.sleep(delay)

    print(f"❌ LocalStack did not become ready after {max_retries} attempts")
    return False


def main():
    """Main initialization function"""
    print("\n" + "=" * 60)
    print("🚀 AlgoItny DynamoDB Initialization")
    print("=" * 60)

    # Step 1: Wait for LocalStack
    if not wait_for_localstack():
        print("\n❌ Initialization failed: LocalStack not available")
        sys.exit(1)

    # Step 2: Initialize DynamoDB table
    if not run_command(
        "python scripts/init_dynamodb.py",
        "Step 1/2: Initializing DynamoDB table"
    ):
        print("\n❌ Initialization failed: DynamoDB initialization failed")
        sys.exit(1)

    # Step 3: Seed default subscription plans to DynamoDB
    if not run_command(
        "python scripts/seed_default_plans.py",
        "Step 2/2: Seeding default subscription plans (DynamoDB)"
    ):
        print("\n⚠️  Warning: Failed to seed default plans")
        print("✅ DynamoDB table created, but plan seeding incomplete")
        sys.exit(0)

    print("\n" + "=" * 60)
    print("✅ DynamoDB initialization completed successfully!")
    print("=" * 60)
    print("\n📊 Summary:")
    print("  ✅ DynamoDB table created")
    print("  ✅ Default subscription plans seeded")
    print("  ✅ System ready for use")
    print("=" * 60)


if __name__ == '__main__':
    main()
