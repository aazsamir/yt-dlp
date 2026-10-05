import time
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
)


class Fc2JavIE(InfoExtractor):
    _VALID_URL = r'https://(?:www\.)?fc2jav\.com/(?P<id>[a-zA-Z0-9_-]+)/?'
    _TESTS = [{
        'url': 'https://fc2jav.com/fc2-ppv-4932321/',
        'md5': '18cbbcdd4860ebfbda10f75a89cbf367',
        'info_dict': {
            'id': 'fc2-ppv-4932321',
            'ext': 'mp4',
            'title': 'FC2PPV 4932321 - Nursing Student Smiles Through 11 Wild Cumshots from Fully Loaded Balls',
            'description': 'md5:4ae187937b9fbfdcd50491872e74ff25',
        },
    }]
    _CACHE_KEY = 'fc2jav'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # <meta itemprop="embedUrl" content="https://fc2tv.vip/e/fc2-ppv-4972774-cac0d084299196ec7af5373b0a33e2d9">
        embed_url = self._html_search_regex(r'<meta itemprop="embedUrl" content="([^"]+)">', webpage, 'embed URL')
        m3u8_part = str(embed_url).split('-')[-1]
        m3u8_url = f'https://fc2tv.vip/p/{m3u8_part}.m3u8'

        title = self._og_search_title(webpage, default=video_id)
        description = self._og_search_description(webpage, default=None)
        m3u8_headers = self._get_m3u8_headers(embed_url)
        segment_token = self._get_segment_token(video_id, webpage, m3u8_headers)

        formats = self._extract_m3u8_formats(
            m3u8_url,
            video_id,
            'mp4',
            entry_protocol='m3u8_native',
            m3u8_id='hls',
            headers=m3u8_headers,
        )

        for fmt in formats:
            fmt['extra_param_to_segment_url'] = urllib.parse.urlencode({'st': segment_token})
            fmt['http_headers'] = m3u8_headers

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'formats': formats,
        }

    def _get_m3u8_headers(self, embed_url):
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'identity',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Origin': 'https://fc2tv.vip',
            'Pragma': 'no-cache',
            'Referer': embed_url,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-GPC': '1',
            'TE': 'trailers',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:154.0) Gecko/20100101 Firefox/154.0',
        }

    def _get_segment_token(self, video_id, webpage, m3u8_headers):
        cache_key = 'segment-token'
        cache_data = self.cache.load(self._CACHE_KEY, cache_key)

        if cache_data and cache_data.get('expires', 0) > time.time():
            return cache_data['token']

        segment_token_url = self._get_segment_token_url(webpage)
        token_headers = {'Range': 'bytes=0-'}
        token_headers.update(m3u8_headers)
        segment_token = self._download_json(segment_token_url, video_id, headers=token_headers)

        if not isinstance(segment_token, dict) or 'st' not in segment_token:
            raise ExtractorError('Failed to retrieve segment token', expected=True)

        token = segment_token['st']
        ttl = int(segment_token.get('ttl', 1800))
        expires = int(time.time()) + ttl
        self.cache.store(self._CACHE_KEY, cache_key, {'token': token, 'expires': expires})

        return token

    def _get_segment_token_url(self, webpage):
        # first, we need to download iframe document, which contains a script tag that loads the player JS file. The player JS file contains the token URL
        # <div id="tab0" class="tab-pane" style="display:flex"><iframe
        #                 src="https://fc2tv.vip/e/fc2-ppv-4972774-cac0d084299196ec7af5373b0a33e2d9" frameborder="0"
        #                 allowfullscreen></iframe></div>
        iframe_url = self._search_regex(r'<div id="tab0"\s+class="tab-pane"\s+style="display:flex"><iframe\s+src="([^"]+)"', webpage, 'iframe URL')
        iframe_page = self._download_webpage(iframe_url, None, 'Downloading iframe document')

        # <script src="/assets/player.7683239bc3d1.js"></script>
        player_js_url = self._search_regex(r'<script src="(/assets/player\.[a-zA-Z0-9]+\.js)"></script>', iframe_page, 'player JS')
        player_js_url = 'https://fc2tv.vip' + str(player_js_url)

        js_page = self._download_webpage(player_js_url, None, 'Downloading player JS')

        # var SEG_HOST = 'c.loadvideo.vip';
        token_host = self._search_regex(r'var SEG_HOST = \'([^\']+)\'', js_page, 'token host')
        # var SEG_TOKEN_URL = 'https://' + SEG_HOST + '/s.v1.1F8t1OQH2xdu7uMgoihDdZrXi6q';
        token_url = self._search_regex(r'var SEG_TOKEN_URL = \'https://\' \+ SEG_HOST \+ \'([^\']+)\'', js_page, 'token URL')

        return f'https://{token_host}{token_url}'
