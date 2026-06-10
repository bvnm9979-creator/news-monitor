#!/usr/bin/env python3
"""
네이버 뉴스 API 프록시 서버
─────────────────────────────────────────
1. 아래 CLIENT_ID / CLIENT_SECRET 를 입력하세요.
2. 터미널에서 실행: python3 naver_proxy.py
3. 브라우저에서 열기: http://localhost:8765

수집된 기사는 data/ 폴더에 날짜별 JSON 파일로 자동 저장됩니다.
"""
import os, re, json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.parse import urlparse, parse_qs, quote
from datetime import datetime, timezone, timedelta

# 로컬 실행: 아래에 직접 입력
# 클라우드 배포: 환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 으로 설정
CLIENT_ID     = os.environ.get('NAVER_CLIENT_ID',     'YOUR_CLIENT_ID')
CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET', 'YOUR_CLIENT_SECRET')
PORT          = int(os.environ.get('PORT', 8765))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
KST      = timezone(timedelta(hours=9))


def today_kst():
    return datetime.now(KST).strftime('%Y-%m-%d')


def date_of_pub(pub_date_str):
    """pubDate 문자열 → KST 날짜 문자열 (YYYY-MM-DD)"""
    try:
        dt = datetime.strptime(pub_date_str.strip(), '%a, %d %b %Y %H:%M:%S %z')
        return dt.astimezone(KST).strftime('%Y-%m-%d')
    except Exception:
        return today_kst()


def save_items(naver_items):
    """오늘 날짜 JSON 파일에 신규 기사를 병합 저장 (URL 기준 중복 제거)"""
    date_str = today_kst()
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, date_str + '.json')

    # 기존 데이터 로드
    existing = {}
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                for item in json.load(f).get('items', []):
                    url = item.get('link') or item.get('originallink', '')
                    if url:
                        existing[url] = item
        except Exception:
            pass

    # 신규 기사 병합 (오늘 날짜만)
    added = 0
    for item in naver_items:
        if date_of_pub(item.get('pubDate', '')) != date_str:
            continue
        url = item.get('link') or item.get('originallink', '')
        if url and url not in existing:
            existing[url] = item
            added += 1

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(
            {'date': date_str, 'items': list(existing.values())},
            f, ensure_ascii=False, indent=2
        )

    if added:
        print(f'[{datetime.now(KST).strftime("%H:%M:%S")}] 신규 기사 {added}건 저장 → {path}')


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/news':
            self._live_news()
        elif path == '/api/history':
            self._history()
        elif path == '/api/dates':
            self._available_dates()
        else:
            self._serve_file('index.html')

    # ── 네이버 API 실시간 조회 ──────────────────────────
    def _live_news(self):
        qs    = parse_qs(urlparse(self.path).query)
        query = qs.get('query', ['김용'])[0]
        url   = ('https://openapi.naver.com/v1/search/news.json'
                 '?query=' + quote(query) + '&display=100&sort=date')
        req = Request(url, headers={
            'X-Naver-Client-Id':     CLIENT_ID,
            'X-Naver-Client-Secret': CLIENT_SECRET,
        })
        try:
            res  = urlopen(req, timeout=10)
            raw  = res.read()
            data = json.loads(raw)
            save_items(data.get('items', []))
            self._write(200, raw, 'application/json; charset=utf-8')
        except Exception as e:
            err = json.dumps({'items': [], 'error': str(e)}).encode()
            self._write(500, err, 'application/json; charset=utf-8')

    # ── 저장된 날짜별 기사 조회 ─────────────────────────
    def _history(self):
        qs   = parse_qs(urlparse(self.path).query)
        date = qs.get('date', [''])[0]
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
            self._json({'items': [], 'error': 'invalid date'})
            return
        file_path = os.path.join(DATA_DIR, date + '.json')
        if os.path.exists(file_path):
            with open(file_path, encoding='utf-8') as f:
                self._json(json.load(f))
        else:
            self._json({'date': date, 'items': []})

    # ── 저장된 날짜 목록 반환 ───────────────────────────
    def _available_dates(self):
        dates = []
        if os.path.exists(DATA_DIR):
            for name in sorted(os.listdir(DATA_DIR), reverse=True):
                if re.match(r'^\d{4}-\d{2}-\d{2}\.json$', name):
                    dates.append(name[:-5])
        self._json({'dates': dates})

    # ── HTML 서빙 ───────────────────────────────────────
    def _serve_file(self, name):
        file_path = os.path.join(BASE_DIR, name)
        try:
            with open(file_path, 'rb') as f:
                body = f.read()
            self._write(200, body, 'text/html; charset=utf-8')
        except FileNotFoundError:
            self._write(404, b'Not Found', 'text/plain')

    def _json(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self._write(200, body, 'application/json; charset=utf-8')

    def _write(self, code, body, content_type):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # 콘솔 로그 숨김


if __name__ == '__main__':
    print(f'\n✅  서버 시작됨')
    print(f'   브라우저에서 열기  →  http://localhost:{PORT}')
    print(f'   기사 저장 폴더     →  {DATA_DIR}')
    print(f'   종료: Ctrl+C\n')
    HTTPServer(('', PORT), Handler).serve_forever()
