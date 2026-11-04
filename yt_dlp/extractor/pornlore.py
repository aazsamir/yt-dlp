import base64

from .common import InfoExtractor


class PornloreIE(InfoExtractor):
    _VALID_URL = r'https://(?:www\.)?pornlore\.com/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://pornlore.com/video/365726',
        'info_dict': {
            'id': '365726',
            'ext': 'mp4',
            'title': 'Foot Goddess Ester using her Slave for Pleasure (foot Slave, High Heels Worship, Foot Worship, Toes)',
            'description': 'md5:a2cc0ab1593db1cbbf7fa9c4352ee8ba',
            'thumbnail': 'https://pornlore.com/storage/images/365726/player.webp',
            'age_limit': 18,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # The player JS obfuscates the m3u8 URL. The embedded string is
        # decoded by: atob(reverse(s[16:-16])) — drop the 16-char prefix and
        # suffix added by the obfuscator, reverse, then base64-decode.
        obfuscated = self._search_regex(
            r'file:\s*f\("([^"]+)"\)', webpage, 'obfuscated m3u8 URL')
        m3u8_url = self._decode_m3u8_url(obfuscated)

        title = self._og_search_title(webpage, default=video_id)
        description = self._og_search_description(webpage, default=None)
        thumbnail = self._og_search_thumbnail(webpage)

        # The m3u8 URL is single-use and rejects browser-like User-Agents
        # (403). Fetch it once with a non-browser User-Agent, then hand the
        # manifest to the native HLS downloader so it is not fetched again.
        headers = {'User-Agent': 'curl/8.0.0'}
        m3u8_doc = self._download_webpage(
            m3u8_url, video_id, note='Downloading m3u8 information', headers=headers)

        formats, _ = self._parse_m3u8_formats_and_subtitles(
            m3u8_doc, m3u8_url, ext='mp4', entry_protocol='m3u8_native', m3u8_id='hls')

        for fmt in formats:
            fmt['hls_media_playlist_data'] = m3u8_doc

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
            'age_limit': 18,
        }

    @staticmethod
    def _decode_m3u8_url(obfuscated):
        return base64.b64decode(obfuscated[16:-16][::-1]).decode()
