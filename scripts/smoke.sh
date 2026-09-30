#!/usr/bin/env bash
# ==============================================================================
# KrishiNet-BRICS - Sovereign Node Smoke Verification Suite
# Verifies a live deployed node in under 60 seconds:
# 1. Health & readiness probe (/health/ready)
# 2. Demo authentication & JWT issuance (/api/v1/auth/dev-login)
# 3. Advisory generation pipeline (/api/v1/fields/{id}/advisory)
# 4. Disease diagnosis ensemble inference (/api/v1/disease/diagnose)
# 5. Messaging webhook / simulator roundtrip (/api/v1/messaging/simulate)
# ==============================================================================

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
DEMO_MODE="${DEMO_MODE:-true}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}🚀 Starting KrishiNet-BRICS Sovereign Node Smoke Test Suite${NC}"
echo -e "${BLUE}Target API: ${API_URL}${NC}"
echo -e "${BLUE}Demo Mode : ${DEMO_MODE}${NC}"
echo -e "${BLUE}=================================================================${NC}"

FAIL_COUNT=0

# Helper function
check_status() {
    local name="$1"
    local status="$2"
    local response="$3"

    if [ "$status" -eq 200 ] || [ "$status" -eq 201 ]; then
        echo -e "  [${GREEN}PASS${NC}] ${name} (HTTP ${status})"
    else
        echo -e "  [${RED}FAIL${NC}] ${name} (Expected 200/201, got HTTP ${status})"
        echo -e "         Response: ${response}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

# ------------------------------------------------------------------------------
# 1. Health & Readiness Probe
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}Step 1: Checking Node Readiness Probe...${NC}"
HEALTH_RES=$(curl -s -w "\n%{http_code}" "${API_URL}/health/ready" || echo '{"status":"error"}\n500')
HEALTH_CODE=$(echo "$HEALTH_RES" | tail -n1)
HEALTH_BODY=$(echo "$HEALTH_RES" | sed '$d')
check_status "Readiness Probe (/health/ready)" "$HEALTH_CODE" "$HEALTH_BODY"

# ------------------------------------------------------------------------------
# 2. Authentication / Dev Login
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}Step 2: Authenticating Demo Farmer Identity...${NC}"
LOGIN_PAYLOAD='{"role":"farmer","country_iso":"IND","full_name":"Smoke Test Farmer","phone_number":"+919876543210"}'
AUTH_RES=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/api/v1/auth/dev-login" \
    -H "Content-Type: application/json" \
    -d "$LOGIN_PAYLOAD" || echo '{"error":"network_fail"}\n500')
AUTH_CODE=$(echo "$AUTH_RES" | tail -n1)
AUTH_BODY=$(echo "$AUTH_RES" | sed '$d')
check_status "Demo Auth Login (/api/v1/auth/dev-login)" "$AUTH_CODE" "$AUTH_BODY"

ACCESS_TOKEN=$(python3 -c "import json; data=json.loads('''$AUTH_BODY'''); print(data.get('access_token', 'demo-token'))" 2>/dev/null || echo "demo-token")

# ------------------------------------------------------------------------------
# 3. Advisory Contract Generation Pipeline
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}Step 3: Generating Field Advisory Contract...${NC}"
ADVISORY_PAYLOAD='{"language":"en","farmer_notes":"Testing smoke verification"}'
ADV_RES=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/api/v1/fields/field-demo-01/advisory" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$ADVISORY_PAYLOAD" || echo '{"error":"advisory_fail"}\n500')
ADV_CODE=$(echo "$ADV_RES" | tail -n1)
ADV_BODY=$(echo "$ADV_RES" | sed '$d')
check_status "Advisory Generation (/fields/field-demo-01/advisory)" "$ADV_CODE" "$ADV_BODY"

# ------------------------------------------------------------------------------
# 4. Disease Diagnosis Inference
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}Step 4: Requesting Disease Diagnosis Inference...${NC}"
# Create a dummy 1x1 GIF/PNG image in memory
DUMMY_IMG="/tmp/smoke_leaf.png"
python3 -c "
import base64
with open('$DUMMY_IMG', 'wb') as f:
    f.write(base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'))
" 2>/dev/null || touch "$DUMMY_IMG"

DISEASE_RES=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/api/v1/disease/diagnose" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -F "image=@${DUMMY_IMG};type=image/png" \
    -F "crop=cotton" \
    -F "latitude=20.5937" \
    -F "longitude=78.9629" || echo '{"error":"disease_fail"}\n500')
DISEASE_CODE=$(echo "$DISEASE_RES" | tail -n1)
DISEASE_BODY=$(echo "$DISEASE_RES" | sed '$d')
check_status "Disease Diagnosis (/disease/diagnose)" "$DISEASE_CODE" "$DISEASE_BODY"

# ------------------------------------------------------------------------------
# 5. Messaging Webhook & Conversation Simulator
# ------------------------------------------------------------------------------
echo -e "\n${YELLOW}Step 5: Testing Messaging Gateway & Conversation Engine...${NC}"
MSG_PAYLOAD='{"from_phone":"+919876543210","body":"1","channel":"whatsapp","country_iso":"IND"}'
MSG_RES=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/api/v1/messaging/simulate" \
    -H "Content-Type: application/json" \
    -d "$MSG_PAYLOAD" || echo '{"error":"messaging_fail"}\n500')
MSG_CODE=$(echo "$MSG_RES" | tail -n1)
MSG_BODY=$(echo "$MSG_RES" | sed '$d')
check_status "Messaging Simulation (/messaging/simulate)" "$MSG_CODE" "$MSG_BODY"

# ------------------------------------------------------------------------------
# Summary & Exit
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}=================================================================${NC}"
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "${GREEN}🎉 SMOKE TEST SUITE PASSED! Sovereign Node is fully operational.${NC}"
    echo -e "${BLUE}=================================================================${NC}"
    exit 0
else
    echo -e "${RED}❌ SMOKE TEST FAILED with ${FAIL_COUNT} failed step(s).${NC}"
    echo -e "${BLUE}=================================================================${NC}"
    exit 1
fi
