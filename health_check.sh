#!/bin/bash

# Health check script for K9LogBot

CONTAINER_NAME="k9logbot"

# Check if container is running
if docker ps --filter "name=$CONTAINER_NAME" --filter "status=running" | grep -q $CONTAINER_NAME; then
    echo "✅ K9LogBot is running"
    
    # Check logs for recent activity
    RECENT_LOGS=$(docker logs --tail 10 $CONTAINER_NAME 2>&1)
    if echo "$RECENT_LOGS" | grep -q "Starting Telegram bot polling"; then
        echo "✅ Bot is actively polling for messages"
    else
        echo "⚠️  Bot may not be polling correctly"
    fi
else
    echo "❌ K9LogBot is not running"
    echo "🔄 Attempting to restart..."
    docker-compose up -d
fi