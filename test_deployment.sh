#!/bin/bash

echo "🔍 Testing K9LogBot Deployment"
echo "=============================="

# Check if container is running
if docker ps --filter "name=k9logbot" --filter "status=running" | grep -q k9logbot; then
    echo "✅ Container is running"
else
    echo "❌ Container is not running"
    exit 1
fi

# Check if database exists
if [ -f "data/k9_log.db" ]; then
    echo "✅ Database file exists"
else
    echo "❌ Database file missing"
fi

# Check I2C
if sudo i2cdetect -y 1 | grep -q "3c\|3d"; then
    echo "✅ OLED display detected"
else
    echo "⚠️  OLED display not detected (check wiring)"
fi

# Check recent logs
echo "📋 Recent logs:"
docker-compose logs --tail=5 k9logbot

echo "🎉 Deployment test complete!"