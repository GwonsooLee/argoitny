# DynamoDB Cleanup Summary

## Date: 2025-10-09

## Overview

Successfully cleaned up the DynamoDB table `algoitny_main` by removing all items except subscription plans and user authentication data.

---

## Cleanup Results

### Items Scanned
- **Total items scanned:** 16

### Items by Type (Before Cleanup)
| Type | Count | Action |
|------|-------|--------|
| `pejob` (Problem Extraction Jobs) | 6 | DELETED |
| `plan` (Subscription Plans) | 2 | **KEPT** |
| `prob` (Problems) | 1 | DELETED |
| `prog` (Job Progress) | 5 | DELETED |
| `sgjob` (Script Generation Jobs) | 1 | DELETED |
| `usr` (Users) | 1 | **KEPT** |

### Summary
- **Items Kept:** 3
  - Subscription Plans: 2
  - Users: 1
- **Items Deleted:** 13
  - Problem Extraction Jobs: 6
  - Problems: 1
  - Job Progress: 5
  - Script Generation Jobs: 1

---

## Remaining Items (Verified)

### Subscription Plans (2 items)

#### Plan 1: Free Plan
- **Plan ID:** 1
- **Name:** Free
- **Description:** Free plan with limited features
- **Max Hints/Day:** 5
- **Max Executions/Day:** 50
- **Max Problems:** -1 (unlimited)
- **Price:** $0
- **Status:** Active

#### Plan 2: Admin Plan
- **Plan ID:** 2
- **Name:** Admin
- **Description:** Full access plan for administrators
- **Max Hints/Day:** -1 (unlimited)
- **Max Executions/Day:** -1 (unlimited)
- **Max Problems:** -1 (unlimited)
- **Price:** $0
- **Status:** Active

### Users (1 item)

#### User: Gwonsoo Lee
- **User ID:** 810628230
- **Email:** gwonsoo.lee@gmail.com
- **Name:** Gwonsoo Lee
- **Google ID:** 100630159390549947987
- **Subscription Plan:** Admin (Plan ID: 2)
- **Status:** Active
- **Staff:** Yes

---

## What Was Deleted

All the following data types were completely removed from the table:

1. **Problems (`prob`)** - 1 item
   - All problem metadata and associated data

2. **Test Cases (`tc`)** - 0 items (none existed)
   - Test case data associated with problems

3. **Script Generation Jobs (`sgjob`)** - 1 item
   - Background job data for script generation

4. **Problem Extraction Jobs (`pejob`)** - 6 items
   - Background job data for problem extraction

5. **Job Progress History (`prog`)** - 5 items
   - Job execution progress tracking data

6. **Search History (`shist`)** - 0 items (none existed)
   - User search history records

7. **Usage Logs (`ulog`)** - 0 items (none existed)
   - API usage tracking logs

8. **Counters (`counter`)** - 0 items (none existed)
   - Auto-increment counter records

---

## Scripts Created

### 1. cleanup_dynamodb.py
- **Location:** `/Users/gwonsoolee/algoitny/backend/cleanup_dynamodb.py`
- **Purpose:** Main cleanup script
- **Features:**
  - Scans entire DynamoDB table
  - Categorizes items by type
  - Batch deletes items (25 per batch)
  - Provides detailed summary
  - Supports `--yes` flag for auto-confirmation

**Usage:**
```bash
# Interactive mode (asks for confirmation)
python cleanup_dynamodb.py

# Auto-confirm mode
python cleanup_dynamodb.py --yes
```

### 2. verify_cleanup.py
- **Location:** `/Users/gwonsoolee/algoitny/backend/verify_cleanup.py`
- **Purpose:** Verify remaining items after cleanup
- **Features:**
  - Scans table and shows remaining items
  - Groups items by type
  - Shows sample items from each type

**Usage:**
```bash
python verify_cleanup.py
```

### 3. show_remaining_details.py
- **Location:** `/Users/gwonsoolee/algoitny/backend/show_remaining_details.py`
- **Purpose:** Show detailed information about remaining items
- **Features:**
  - Uses repository pattern to fetch data
  - Shows full details of subscription plans
  - Shows full details of users
  - Provides summary statistics

**Usage:**
```bash
python show_remaining_details.py
```

---

## DynamoDB Table Structure

### Table Name
`algoitny_main`

### Primary Key
- **Partition Key (PK):** String
- **Sort Key (SK):** String

### Global Secondary Indexes (GSIs)
- **GSI1:** GSI1PK, GSI1SK
- **GSI2:** GSI2PK, GSI2SK (optional)
- **GSI3:** GSI3PK, GSI3SK

### Item Type Attribute
All items have a `tp` (type) attribute that identifies the item type:
- `plan` - Subscription plans
- `usr` - Users
- `prob` - Problems (DELETED)
- `tc` - Test cases (DELETED)
- `sgjob` - Script generation jobs (DELETED)
- `pejob` - Problem extraction jobs (DELETED)
- `prog` - Job progress (DELETED)
- `shist` - Search history (DELETED)
- `ulog` - Usage logs (DELETED)
- `counter` - Auto-increment counters (DELETED)

---

## Execution Details

### Environment
- **Python Version:** 3.12
- **Virtual Environment:** `.venv`
- **AWS Region:** Configured via environment
- **DynamoDB Endpoint:** LocalStack or AWS (based on LOCALSTACK_URL env var)

### Execution Log
```
================================================================================
DynamoDB Cleanup Script
================================================================================

This script will DELETE all items except:
  - Subscription plans (tp = 'plan')
  - User authentication data (tp = 'usr')

================================================================================
Scanning DynamoDB table...
Total items scanned: 16

--------------------------------------------------------------------------------
ITEMS BY TYPE:
  pejob          :      6 items (DELETE)
  plan           :      2 items (KEEP)
  prob           :      1 items (DELETE)
  prog           :      5 items (DELETE)
  sgjob          :      1 items (DELETE)
  usr            :      1 items (KEEP)
--------------------------------------------------------------------------------

Total items to KEEP:   3
Total items to DELETE: 13

================================================================================

Auto-confirming deletion of 13 items (--yes flag provided)

Deleting 13 items in 1 batches...
  Batch 1/1 completed (13 deleted)

================================================================================
CLEANUP SUMMARY
================================================================================

ITEMS SCANNED BY TYPE:
  pejob          :      6
  plan           :      2
  prob           :      1
  prog           :      5
  sgjob          :      1
  usr            :      1
  TOTAL          :     16

ITEMS KEPT (NOT DELETED):
  plan           :      2
  usr            :      1
  TOTAL KEPT     :      3

ITEMS DELETED:
  pejob          :      6
  prob           :      1
  prog           :      5
  sgjob          :      1
  TOTAL DELETED  :     13

================================================================================

Cleanup completed successfully!
```

---

## Post-Cleanup Status

### Current Table Contents
- **Total Items:** 3
- **Subscription Plans:** 2 (Free, Admin)
- **Users:** 1 (gwonsoo.lee@gmail.com)
- **All Other Data:** DELETED

### Data Integrity
- All user authentication data preserved
- All subscription plan configurations preserved
- User-to-plan relationships intact
- Ready for fresh data ingestion

---

## Notes

1. **Batch Deletion:** Items were deleted in batches of 25 (DynamoDB limit) for optimal performance
2. **No Errors:** All 13 deletions completed successfully with no errors
3. **Verification:** Post-cleanup verification confirmed only 3 items remain
4. **Data Safety:** Subscription plans and user authentication data remain fully intact
5. **Clean Slate:** Table is now ready for new problem data, jobs, and logs

---

## Recommendations

1. **Future Cleanups:** Use the `cleanup_dynamodb.py` script for similar operations
2. **Backup:** Consider implementing a backup strategy before running cleanup in production
3. **Monitoring:** Set up CloudWatch alarms for DynamoDB table metrics
4. **Cost Optimization:** With fewer items, consider adjusting provisioned capacity if applicable
5. **Testing:** Verify application functionality with the cleaned table

---

## Contact

**Executed By:** DynamoDB Architecture Specialist
**Date:** October 9, 2025
**Status:** ✅ Successfully Completed
