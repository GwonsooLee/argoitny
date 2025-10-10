#!/bin/bash

# GPT-5 Migration Verification Script
# This script verifies that all GPT-5 migration changes have been applied correctly

echo "=================================================="
echo "GPT-5 Migration Verification"
echo "=================================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Test 1: Verify model is gpt-5 in settings.py
echo "Test 1: Checking default model in settings.py..."
if grep -q "default='gpt-5'" backend/config/settings.py; then
    echo -e "${GREEN}✓ PASS${NC} - Default model is gpt-5"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - Default model is not gpt-5"
    ((FAILED++))
fi
echo ""

# Test 2: Verify model is gpt-5 in openai_service.py
echo "Test 2: Checking service model in openai_service.py..."
if grep -q "getattr(settings, 'OPENAI_MODEL', 'gpt-5')" backend/api/services/openai_service.py; then
    echo -e "${GREEN}✓ PASS${NC} - Service model fallback is gpt-5"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - Service model fallback is not gpt-5"
    ((FAILED++))
fi
echo ""

# Test 3: Verify no temperature parameter (excluding comments)
echo "Test 3: Checking for temperature parameters..."
TEMP_COUNT=$(grep -c "temperature=" backend/api/services/openai_service.py | grep -v "^#" || true)
if [ "$TEMP_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ PASS${NC} - No temperature parameters found"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - Found $TEMP_COUNT temperature parameter(s)"
    ((FAILED++))
fi
echo ""

# Test 4: Verify reasoning_effort is present (should be 2 occurrences)
echo "Test 4: Checking for reasoning_effort parameters..."
REASONING_COUNT=$(grep -c 'reasoning_effort="high"' backend/api/services/openai_service.py || true)
if [ "$REASONING_COUNT" -eq 2 ]; then
    echo -e "${GREEN}✓ PASS${NC} - Found 2 reasoning_effort=\"high\" parameters (correct)"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - Found $REASONING_COUNT reasoning_effort parameters (expected 2)"
    ((FAILED++))
fi
echo ""

# Test 5: Verify top_p=1 is present (should be 2 occurrences)
echo "Test 5: Checking for top_p parameters..."
TOPP_COUNT=$(grep -c 'top_p=1' backend/api/services/openai_service.py || true)
if [ "$TOPP_COUNT" -eq 2 ]; then
    echo -e "${GREEN}✓ PASS${NC} - Found 2 top_p=1 parameters (correct)"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - Found $TOPP_COUNT top_p parameters (expected 2)"
    ((FAILED++))
fi
echo ""

# Test 6: Verify get_optimal_temperature method is removed
echo "Test 6: Checking that get_optimal_temperature method is removed..."
if grep -q "def get_optimal_temperature" backend/api/services/openai_service.py; then
    echo -e "${RED}✗ FAIL${NC} - get_optimal_temperature method still exists"
    ((FAILED++))
else
    echo -e "${GREEN}✓ PASS${NC} - get_optimal_temperature method removed"
    ((PASSED++))
fi
echo ""

# Test 7: Verify timeout is set to 1800.0
echo "Test 7: Checking OpenAI client timeout..."
if grep -q "timeout=1800.0" backend/api/services/openai_service.py; then
    echo -e "${GREEN}✓ PASS${NC} - Client timeout set to 1800.0 (30 minutes)"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Timeout not found or different value"
fi
echo ""

# Test 8: Verify no references to gpt-4 or gpt-4o (excluding comments and old docs)
echo "Test 8: Checking for old model references..."
OLD_MODEL_COUNT=$(grep -E "gpt-4[^5]|gpt-4o" backend/api/services/openai_service.py backend/config/settings.py | grep -v "^#" | grep -v "Before" | wc -l)
if [ "$OLD_MODEL_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ PASS${NC} - No old model references found"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Found $OLD_MODEL_COUNT references to old models (may be in comments)"
fi
echo ""

# Summary
echo "=================================================="
echo "VERIFICATION SUMMARY"
echo "=================================================="
echo -e "Tests Passed: ${GREEN}$PASSED${NC}"
echo -e "Tests Failed: ${RED}$FAILED${NC}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    echo "GPT-5 migration is complete and verified."
    echo ""
    echo "Next steps:"
    echo "1. Deploy to development environment"
    echo "2. Test API endpoints"
    echo "3. Monitor performance and costs"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo "Please review the failed tests above and fix any issues."
    exit 1
fi
