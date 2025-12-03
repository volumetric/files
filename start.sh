#!/bin/bash

echo "Starting YouTube Audio Downloader..."
echo ""
echo "Make sure you have installed the requirements:"
echo "  pip install flask flask-cors yt-dlp --break-system-packages"
echo ""
echo "The server will start at http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""

python server.py
