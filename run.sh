#!/bin/bash
# Quick setup and run script for the Interactive Research Tool

echo "🚀 Setting up Interactive Research Paper Discovery Tool..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file template..."
    echo "GEMINI_API_KEY=" > .env
    echo "⚠️  Please add your Gemini API key to the .env file before running"
    echo "   You can get an API key from: https://ai.google.dev/"
    exit 1
fi

# Check if API key is set
if grep -q "GEMINI_API_KEY=$" .env; then
    echo "⚠️  Please set your GEMINI_API_KEY in the .env file"
    echo "   Edit .env and add: GEMINI_API_KEY=your_key_here"
    exit 1
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
python3 -c "import requests, dotenv, bs4, PyPDF2" 2>/dev/null || {
    echo "Installing missing dependencies..."
    pip install -r requirements.txt --user
}

# Run the interactive application
echo "🎯 Starting Interactive Research Tool..."
echo ""
python3 interactive_app.py