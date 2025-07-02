#!/bin/bash

# Test the complete conversation flow with question generation

echo "1. Starting new conversation with initial job requirements..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/chat/conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need a VP of Sales for FlowAI, a Series A fintech startup. They are a B2B SaaS company doing AI-powered financial analytics. We need someone who can take us from $2M to $10M ARR in the next 18 months."
  }')

echo "$RESPONSE" | python -m json.tool

# Extract conversation_id from response
CONVERSATION_ID=$(echo "$RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['conversation_id'])")

echo -e "\n\n2. Answering first question..."
RESPONSE2=$(curl -s -X POST "http://localhost:8000/api/chat/conversation" \
  -H "Content-Type: application/json" \
  -d "{
    \"conversation_id\": \"$CONVERSATION_ID\",
    \"message\": \"They need to build an outbound sales motion from scratch and transition us from founder-led sales. Experience with PLG to sales-led transition would be ideal.\"
  }")

echo "$RESPONSE2" | python -m json.tool

echo -e "\n\n3. Getting conversation progress..."
curl -s -X GET "http://localhost:8000/api/chat/conversation/$CONVERSATION_ID/progress" | python -m json.tool

echo -e "\n\n4. Getting conversation summary..."
curl -s -X GET "http://localhost:8000/api/chat/conversation/$CONVERSATION_ID" | python -m json.tool