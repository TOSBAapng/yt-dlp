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
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            # YouTube format engellerini tamamen aşan istemci kombinasyonu
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv_embedded', 'mweb'],
                    'player_skip': ['webpage', 'configs']
                }
            }
        }

        # Çerez verisi varsa formatını düzeltip geçici dosyaya yaz
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
                
                # Formats dizisindeki doğrudan oynatılabilir MP4 / WebM akışını bul
                if 'formats' in info and info['formats']:
                    # 1. Öncelik: Hem ses hem video içeren doğrudan oynatılabilir bağlantı
                    for f in info['formats']:
                        if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('url'):
                            stream_url = f.get('url')
                            break
                    
                    # 2. Öncelik: Bütünleşik bulunamazsa geçerli ilk medya adresi
                    if not stream_url:
                        for f in reversed(info['formats']):
                            if f.get('url'):
                                stream_url = f.get('url')
                                break
                
                if not stream_url:
                    stream_url = info.get('url')

                response = {
                    'status': 'success',
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'url': stream_url,
                    'thumbnail': info.get('thumbnail')
                }
        except Exception as e:
            response = {'status': 'error', 'message': str(e)}
        finally:
            if cookie_file_path and os.path.exists(cookie_file_path):
                os.remove(cookie_file_path)

        self.wfile.write(json.dumps(response).encode('utf-8'))
        return
