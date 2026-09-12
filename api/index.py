from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import os
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
            response = {
                'status': 'error', 
                'message': 'Lutfen url parametresi gonderin.'
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        cookie_data = os.environ.get('YOUTUBE_COOKIES', '')
        cookie_file_path = None

        ydl_opts = {
            # 'format': 'all' sayesinde yt-dlp "Requested format is not available" hatası fırlatmaz
            'format': 'all',
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            # Embed engeline ve PoToken kısıtlamasına takılmayan istemciler
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android_vr', 'mweb'],
                    'player_skip': ['configs', 'webpage']
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
                
                stream_url = None
                formats = info.get('formats', [])
                
                # 1. Ses ve Video barındıran doğrudan akış (MP4 / HLS)
                for f in formats:
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('url'):
                        stream_url = f.get('url')
                        break

                # 2. Bulunamazsa geçerli video akışı (mhtml/storyboard hariç)
                if not stream_url:
                    for f in formats:
                        if f.get('vcodec') != 'none' and f.get('url') and not str(f.get('ext')).startswith('mhtml'):
                            stream_url = f.get('url')
                            break

                # 3. Son çare: Herhangi bir geçerli medya bağlantısı
                if not stream_url:
                    for f in reversed(formats):
                        if f.get('url') and not str(f.get('ext')).startswith('mhtml'):
                            stream_url = f.get('url')
                            break

                if not stream_url:
                    stream_url = info.get('url')

                response = {
                    'status': 'success' if stream_url else 'error',
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'url': stream_url if stream_url else None,
                    'thumbnail': info.get('thumbnail')
                }
        except Exception as e:
            response = {'status': 'error', 'message': str(e)}
        finally:
            if cookie_file_path and os.path.exists(cookie_file_path):
                os.remove(cookie_file_path)

        self.wfile.write(json.dumps(response).encode('utf-8'))
        return
