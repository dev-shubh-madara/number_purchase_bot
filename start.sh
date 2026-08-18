#!/bin/bash

echo "======================================"
echo "    🚀 STARTING NUMBOTT TELETHON 🚀    "
echo "======================================"

# Navigate to script directory
cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found! Creating one..."
    python3 -m venv venv
    echo "✅  Virtual environment created."
fi

# Activate venv
source venv/bin/activate

# Install requirements if present
if [ -f "requirements.txt" ]; then
    echo "📦  Checking and installing dependencies..."
    pip install -r requirements.txt
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file is missing! Please create one using the template."
    exit 1
fi

echo "🟢  Starting the bot..."
python main.py

