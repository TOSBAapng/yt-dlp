export default async function handler(req, res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    
    const { url } = req.query;

    if (!url) {
        return res.status(400).json({ success: false, error: 'Lütfen bir YouTube linki girin.' });
    }

    try {
        const response = await fetch(`https://api.vreden.web.id/api/ytmp4?url=${encodeURIComponent(url)}`);
        const data = await response.json();

        if (data && data.result && data.result.download && data.result.download.url) {
            return res.status(200).json({
                success: true,
                title: data.result.title || 'Video',
                download_url: data.result.download.url
            });
        }

        return res.status(400).json({ success: false, error: 'Video linki alınamadı.' });

    } catch (err) {
        return res.status(500).json({ success: false, error: 'Bir sunucu hatası oluştu.' });
    }
}
