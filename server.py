from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import re
from pathlib import Path
import zipfile
import shutil
from io import BytesIO

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
        
        # Base options
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        
        # Check for chapters first
        # We need to extract info to see if chapters exist
        with yt_dlp.YoutubeDL(dict(ydl_opts)) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                chapters = info.get('chapters')
                video_title = info.get('title', 'audio')
            except Exception as e:
                raise e

        has_chapters = bool(chapters and len(chapters) > 0)
        
        if has_chapters:
            ydl_opts['split_chapters'] = True
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegSplitChapters',
                'force_keyframes': False,
            })
            ydl_opts['outtmpl'] = {
                'default': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'chapter': os.path.join(temp_dir, '%(title)s - %(section_number)03d - %(section_title)s.%(ext)s')
            }
        else:
            ydl_opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
            
        # Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            
        # Collect MP3 files
        mp3_files = []
        for file in os.listdir(temp_dir):
            if file.endswith('.mp3'):
                mp3_files.append(os.path.join(temp_dir, file))
        
        # If we have chapters, filter out the full file
        if has_chapters and len(mp3_files) > 1:
            # Chapter files have " - 001 - " pattern (from our template)
            chapter_pattern = re.compile(r' - \d{3} - ')
            chapter_files = [f for f in mp3_files if chapter_pattern.search(os.path.basename(f))]
            
            # Only switch to chapter files if we actually found them
            if chapter_files:
                mp3_files = chapter_files
        
        if not mp3_files:
            return jsonify({'error': 'Failed to create MP3 file(s)'}), 500
        
        if not mp3_files:
            return jsonify({'error': 'Failed to create MP3 file(s)'}), 500
            
        safe_title = sanitize_filename(video_title)
        
        # If multiple files (chapters), zip them
        if len(mp3_files) > 1:
            memory_file = BytesIO()
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                for mp3_path in sorted(mp3_files):
                    # Add file to zip with just the filename (no path)
                    zf.write(mp3_path, os.path.basename(mp3_path))
            
            memory_file.seek(0)
            
            # Clean up temp directory
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            
            return send_file(
                memory_file,
                as_attachment=True,
                download_name=f"{safe_title}.zip",
                mimetype='application/zip'
            )
        else:
            # Single file
            mp3_file = mp3_files[0]
            with open(mp3_file, 'rb') as f:
                mp3_data = f.read()
            
            # Clean up temp directory
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            
            return send_file(
                BytesIO(mp3_data),
                as_attachment=True,
                download_name=os.path.basename(mp3_file),
                mimetype='audio/mpeg'
            )
    
    except Exception as e:
        # Clean up temp directory on error
        if temp_dir:
            try:
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
