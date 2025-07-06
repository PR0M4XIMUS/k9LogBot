#!/bin/bash

# K9LogBot Deployment Script for Raspberry Pi

echo "🐕 K9LogBot Deployment Script"
echo "=============================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your bot configuration:"
    echo "TELEGRAM_BOT_TOKEN=your_bot_token_here"
    echo "YOUR_TELEGRAM_CHAT_ID=your_chat_id_here"
    exit 1
fi

# Create data directory
mkdir -p ./data

# Stop existing container if running
echo "🛑 Stopping existing container..."
docker-compose down

# Build and start the container
echo "🔨 Building and starting K9LogBot..."
docker-compose up -d --build

# Check if container is running
if [ $? -eq 0 ]; then
    echo "✅ K9LogBot is now running!"
    echo "📊 To view logs: docker-compose logs -f"
    echo "🔄 To restart: docker-compose restart"
    echo "🛑 To stop: docker-compose down"
else
    echo "❌ Failed to start K9LogBot"
    exit 1
fi