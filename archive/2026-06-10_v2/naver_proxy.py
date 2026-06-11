#!/usr/bin/env python3
"""
네이버 뉴스 API 프록시 서버
─────────────────────────────────────────
1. 아래 CLIENT_ID / CLIENT_SECRET 를 입력하세요.
2. 터미널에서 실행: python3 naver_proxy.py
3. 브라우저에서 열기: http://localhost:8765
"""
import os, json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.parse import urlparse, parse_qs, quote

# ── 여기에 네이버 API 키를 입력하세요 ─────────────────
CLIENT_ID     = 'YOUR_CLIENT_ID'
CLIENT_SECRET = 'YOUR_CLIENT_SECRET'
# ─────────────────────────────────────────────────────

PORT     = 8765
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path.startswith('/api/news'):
            self._proxy_news()
        else:
            self._serve_html()

    def _proxy_news(self):
        qs    = parse_qs(urlparse(self.path).query)
        query = qs.get('query', ['김용'])[0]
        url   = (
            'https://openapi.naver.com/v1/search/news.json'
            '?query=' + quote(query) + '&display=100&sort=date'
        )
        req = Request(url, headers={
            'X-Naver-Client-Id':     CLIENT_ID,
            'X-Naver-Client-Secret': CLIENT_SECRET,
        })
        try:
            res  = urlopen(req, timeout=10)
            body = res.read()
            code = 200
        except Exception as e:
            body = json.dumps({'items': [], 'error': str(e)}).encode()
            code = 500

        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(body)

    def _serve_html(self):
        path = os.path.join(BASE_DIR, 'index.html')
        try:
            with open(path, 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
        except FileNotFoundError:
            body = b'index.html not found'
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # 콘솔 로그 숨김


if __name__ == '__main__':
    print(f'\n✅  프록시 서버 시작됨')
    print(f'   브라우저에서 열기 → http://localhost:{PORT}')
    print(f'   종료: Ctrl+C\n')
    HTTPServer(('localhost', PORT), Handler).serve_forever()
