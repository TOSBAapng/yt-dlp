from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import os
import urllib.request
import urllib.parse
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

        video_id = None
        if 'v=' in url:
            video_id = url.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]

        stream_url = None
        title = None
        duration = None
        thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else None

        # --- YÖNTEM 1: Cobalt API Proxy (En Yüksek Başarı Oranı & Doğrudan MP4) ---
        if video_id:
            try:
                cobalt_instances = [
                    "https://api.cobalt.tools/api/json",
                    "https://cobalt-api.kwippy.com/api/json"
                ]
                payload = json.dumps({
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "videoQuality": "720"
                }).encode('utf-8')

                for cob_url in cobalt_instances:
                    try:
                        req = urllib.request.Request(
                            cob_url, 
                            data=payload, 
                            headers={
                                'Content-Type': 'application/json',
                                'Accept': 'application/json',
                                'User-Agent': 'Mozilla/5.0'
                            },
                            method='POST'
                        )
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            if resp.status == 200:
                                cob_data = json.loads(resp.read().decode('utf-8'))
                                if cob_data.get('url'):
                                    stream_url = cob_data.get('url')
                                    break
                    except Exception:
                        continue
            except Exception:
                pass

        # --- YÖNTEM 2: Piped API Fallback ---
        if not stream_url and video_id:
            piped_instances = [
                f"https://pipedapi.kavin.rocks/streams/{video_id}",
                f"https://api.piped.vicr.in/streams/{video_id}"
            ]
            for piped_url in piped_instances:
                try:
                    req = urllib.request.Request(piped_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=4) as resp:
                        if resp.status == 200:
                            p_data = json.loads(resp.read().decode('utf-8'))
                            title = p_data.get('title')
                            duration = p_data.get('duration')
                            # MP4 formatları içinden kombine akış çek
                            for st in p_data.get('videoStreams', []):
                                if st.get('url') and st.get('videoOnly') is False:
                                    stream_url = st.get('url')
                                    break
                            if stream_url:
                                break
                except Exception:
                    continue

        # --- YÖNTEM 3: Standart yt-dlp Denemesi ---
        if not stream_url:
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
                    if not title:
                        title = info.get('title')
                    if not duration:
                        duration = info.get('duration')
                    if not thumbnail:
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

        # Yanıt Oluşturma
        if stream_url:
            response = {
                'status': 'success',
                'title': title if title else "YouTube Video",
                'duration': duration,
                'url': stream_url,
                'thumbnail': thumbnail
            }
        else:
            response = {
                'status': 'error',
                'message': 'Video akis adresi alinmadi. Baglantiyi kontrol edin.'
            }

        self.wfile.write(json.dumps(response).encode('utf-8'))
        return
