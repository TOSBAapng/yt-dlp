from flask import Flask, request, jsonify
import yt_dlp

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    url = request.args.get('url') or (request.json and request.json.get('url'))
    
    if not url:
        return jsonify({'status': 'error', 'message': 'Lutfen url parametresi gonderin.'}), 400

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return jsonify({
                'status': 'success',
                'title': info.get('title'),
                'duration': info.get('duration'),
                'url': info.get('url'),
                'thumbnail': info.get('thumbnail')
            })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run()
