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
            'format': 'all',
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            # Gerçek video akışı döndüren TV ve Creator istemcileri
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv', 'android_creator', 'mweb'],
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
                
                # Storyboard/Resim linklerini filtreleyen yardımcı fonksiyon
                def is_real_media(f_url, ext):
                    if not f_url:
                        return False
                    f_url_str = str(f_url).lower()
                    ext_str = str(ext).lower()
                    if 'storyboard' in f_url_str or 'i.ytimg.com' in f_url_str:
                        return False
                    if ext_str in ['mhtml', 'jpg', 'png', 'webp']:
                        return False
                    return True

                # 1. Öncelik: Hem Ses hem Video barındıran gerçek medya akışı
                for f in formats:
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        if is_real_media(f.get('url'), f.get('ext')):
                            stream_url = f.get('url')
                            break

                # 2. Öncelik: Sadece Video barındıran medya akışı
                if not stream_url:
                    for f in formats:
                        if f.get('vcodec') != 'none':
                            if is_real_media(f.get('url'), f.get('ext')):
                                stream_url = f.get('url')
                                break

                # 3. Öncelik: Resim olmayan herhangi bir video/ses linki (.mp4 / .m3u8 vb.)
                if not stream_url:
                    for f in reversed(formats):
                        if is_real_media(f.get('url'), f.get('ext')):
                            stream_url = f.get('url')
                            break

                response = {
                    'status': 'success' if stream_url else 'error',
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
