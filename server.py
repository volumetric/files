from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import re
from pathlib import Path

app = Flask(__name__)
CORS(app)

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

@app.route('/')
def index():
    """Serve the HTML file"""
    return send_file('./youtube-audio-downloader.html')

@app.route('/api/download', methods=['POST'])
def download_audio():
    temp_dir = None
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        # Create a temporary directory for downloads
        temp_dir = tempfile.mkdtemp()
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        # Download the audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'audio')
            
            # Find the downloaded MP3 file
            mp3_file = None
            for file in os.listdir(temp_dir):
                if file.endswith('.mp3'):
                    mp3_file = os.path.join(temp_dir, file)
                    break
            
            if not mp3_file or not os.path.exists(mp3_file):
                return jsonify({'error': 'Failed to create MP3 file'}), 500
            
            # Sanitize the filename
            safe_title = sanitize_filename(video_title)
            download_name = f"{safe_title}.mp3"
            
            # Read the file into memory
            with open(mp3_file, 'rb') as f:
                mp3_data = f.read()
            
            # Clean up the temp directory
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass
            
            # Create response with the file data
            from io import BytesIO
            return send_file(
                BytesIO(mp3_data),
                as_attachment=True,
                download_name=download_name,
                mimetype='audio/mpeg'
            )
    
    except Exception as e:
        # Clean up temp directory on error
        if temp_dir:
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass
        
        error_message = str(e)
        if 'not a valid URL' in error_message or 'Unsupported URL' in error_message:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        return jsonify({'error': f'Download failed: {error_message}'}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("YouTube Audio Downloader Server")
    print("=" * 50)
    print("Server starting at: http://localhost:5005")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5005, debug=False, threaded=True)
