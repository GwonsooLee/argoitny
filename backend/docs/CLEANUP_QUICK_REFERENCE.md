# DynamoDB Cleanup - Quick Reference

## What Was Done

**Deleted ALL items EXCEPT:**
- ✅ Subscription Plans (2 items)
- ✅ User Authentication Data (1 user)

**Deleted Items (Total: 13):**
- ❌ Problems: 1
- ❌ Script Generation Jobs: 1
- ❌ Problem Extraction Jobs: 6
- ❌ Job Progress History: 5

---

## Current Table State

```
Total Items: 3

Subscription Plans (2):
├── Plan #1: Free (5 hints/day, 50 executions/day)
└── Plan #2: Admin (unlimited everything)

Users (1):
└── gwonsoo.lee@gmail.com (Admin plan, Staff user)
```

---

## Scripts Available

### 1. Cleanup Script
```bash
cd /Users/gwonsoolee/algoitny/backend
source .venv/bin/activate
python cleanup_dynamodb.py --yes
```

### 2. Verify Cleanup
```bash
cd /Users/gwonsoolee/algoitny/backend
source .venv/bin/activate
python verify_cleanup.py
```

### 3. Show Details
```bash
cd /Users/gwonsoolee/algoitny/backend
source .venv/bin/activate
python show_remaining_details.py
```

---

## Item Types Reference

| Type | Description | Status |
|------|-------------|--------|
| `plan` | Subscription plans | ✅ KEPT |
| `usr` | User accounts | ✅ KEPT |
| `prob` | Problems | ❌ DELETED |
| `tc` | Test cases | ❌ DELETED |
| `sgjob` | Script generation jobs | ❌ DELETED |
| `pejob` | Problem extraction jobs | ❌ DELETED |
| `prog` | Job progress history | ❌ DELETED |
| `shist` | Search history | ❌ DELETED |
| `ulog` | Usage logs | ❌ DELETED |
| `counter` | Auto-increment counters | ❌ DELETED |

---

## Key Files

```
/Users/gwonsoolee/algoitny/backend/
├── cleanup_dynamodb.py              # Main cleanup script
├── verify_cleanup.py                # Verification script
├── show_remaining_details.py        # Detailed view script
├── DYNAMODB_CLEANUP_SUMMARY.md      # Full cleanup report
└── CLEANUP_QUICK_REFERENCE.md       # This file
```

---

## Status: ✅ COMPLETED

- **Date:** October 9, 2025
- **Items Deleted:** 13
- **Items Kept:** 3
- **Errors:** 0
- **Success Rate:** 100%
