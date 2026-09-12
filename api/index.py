from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import os
import urllib.request
import tempfile
import yt_dlp

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        
        url_list = query_params.get('url')
        url = url_list[0] if url_list else None

        self.send_response(200 if url else 400)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if not url:
            response = {'status': 'error', 'message': 'Lutfen url parametresi gonderin.'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        # Video ID çıkarma
        video_id = None
        if 'v=' in url:
            video_id = url.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]

        stream_url = None
        title = None
        duration = None
        thumbnail = None

        # --- YÖNTEM 1: yt-dlp ile Doğrudan Çekme Denemesi ---
        cookie_data = os.environ.get('YOUTUBE_COOKIES', '')
        cookie_file_path = None

        ydl_opts = {
            'format': 'all',
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android', 'mweb']
                }
            }
        }

        if cookie_data and len(cookie_data.strip()) > 0:
            formatted_cookies = cookie_data.replace('\\n', '\n')
            temp_cookie = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt')
            temp_cookie.write(formatted_cookies)
            temp_cookie.close()
            cookie_file_path = temp_cookie.name
            ydl_opts['cookiefile'] = cookie_file_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title')
                duration = info.get('duration')
                thumbnail = info.get('thumbnail')
                
                formats = info.get('formats', [])
                for f in formats:
                    f_url = str(f.get('url', ''))
                    ext = str(f.get('ext', ''))
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        if 'storyboard' not in f_url and ext not in ['mhtml', 'jpg', 'png']:
                            stream_url = f_url
                            break
        except Exception:
            pass
        finally:
            if cookie_file_path and os.path.exists(cookie_file_path):
                os.remove(cookie_file_path)

        # --- YÖNTEM 2: Invidious API Fallback (IP Bloklarını %100 Aşar) ---
        if not stream_url and video_id:
            invidious_instances = [
                f"https://invidious.nerdvpn.de/api/v1/videos/{video_id}",
                f"https://inv.tux.pizza/api/v1/videos/{video_id}",
                f"https://invidious.drgns.space/api/v1/videos/{video_id}"
            ]
            
            for instance_url in invidious_instances:
                try:
                    req = urllib.request.Request(instance_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=4) as response_net:
                        if response_net.status == 200:
                            data = json.loads(response_net.read().decode('utf-8'))
                            if not title:
                                title = data.get('title')
                            if not duration:
                                duration = data.get('lengthSeconds')
                            if not thumbnail and data.get('videoThumbnails'):
                                thumbnail = data['videoThumbnails'][0].get('url')

                            # Bütünleşik MP4 formatlarını tara
                            for fmt in data.get('formatStreams', []):
                                if fmt.get('url') and 'video/mp4' in fmt.get('container', '').lower() or fmt.get('qualityLabel'):
                                    stream_url = fmt.get('url')
                                    break
                            
                            if stream_url:
                                break
                except Exception:
                    continue

        # Yanıt oluşturma
        if stream_url:
            response = {
                'status': 'success',
                'title': title,
                'duration': duration,
                'url': stream_url,
                'thumbnail': thumbnail
            }
        else:
            response = {
                'status': 'error',
                'message': 'Video akis adresi alinamadi. Lutfen video ID veya baglantiyi kontrol edin.'
            }

        self.wfile.write(json.dumps(response).encode('utf-8'))
        return
