#!/usr/bin/env python3
"""
Threat Intel Dashboard — RSS Aggregator Backend
stdlib only, no pip required.

Run:  python server.py   (or  py server.py  on Windows)
Open: http://localhost:5100
"""

import json, re, time, threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request as UReq
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

PORT      = 5100
CACHE_DIR = Path(__file__).parent / 'cache'
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL = 900   # 15 minutes

FEEDS = [
    {'name': 'Bleeping Computer',  'url': 'https://www.bleepingcomputer.com/feed/',                        'default_sector': 'Malware / Ransomware'},
    {'name': 'SANS ISC',           'url': 'https://isc.sans.edu/rssfeed_full.xml',                         'default_sector': 'Incident Analysis'},
    {'name': 'Unit 42',            'url': 'https://unit42.paloaltonetworks.com/feed/',                     'default_sector': 'Threat Research'},
    {'name': 'Dark Reading',       'url': 'https://www.darkreading.com/rss.xml',                           'default_sector': 'General Security'},
    {'name': 'CISA',               'url': 'https://www.cisa.gov/cybersecurity-advisories/all.xml',         'default_sector': 'Government Advisory'},
    {'name': 'Check Point',        'url': 'https://research.checkpoint.com/feed/',                         'default_sector': 'Threat Research'},
    {'name': 'CrowdStrike',        'url': 'https://www.crowdstrike.com/blog/feed/',                        'default_sector': 'Threat Intelligence'},
    {'name': 'Microsoft Security', 'url': 'https://www.microsoft.com/en-us/security/blog/feed/',           'default_sector': 'Microsoft Security'},
    {'name': 'WeLiveSecurity',     'url': 'https://www.welivesecurity.com/en/feed/',                       'default_sector': 'Malware / APT'},
]

SECTOR_KEYWORDS = [
    (['ransomware', 'lockbit', 'blackcat', 'clop', 'alphv', 'ransom demand'],   'Ransomware'),
    (['phishing', 'spear-phishing', 'credential harvest', 'bec ', 'email fraud'],'Phishing'),
    (['cve-', 'zero-day', '0-day', 'patch tuesday', 'exploit', 'rce', 'remote code execution', 'sql injection', 'xss', 'buffer overflow'], 'Vulnerability'),
    (['malware', 'trojan', ' rat ', 'backdoor', 'botnet', 'rootkit', 'spyware', 'infostealer', 'loader', 'dropper', 'wiper'], 'Malware'),
    (['apt ', 'apt-', 'nation-state', 'nation state', 'espionage', 'lazarus', 'cozy bear', 'fancy bear', 'sandworm', 'hafnium', 'volt typhoon', 'salt typhoon', 'unc', 'ta4'], 'APT / Nation-State'),
    (['advisory', ' ics ', 'scada', 'ot security', 'critical infrastructure', 'operational technology', 'industrial control'], 'ICS / Advisory'),
    (['supply chain', 'typosquat', 'dependency confusion', 'open source attack', 'package hijack'], 'Supply Chain'),
    (['cloud ', 'aws ', 'azure ', 'gcp ', 's3 bucket', 'kubernetes', 'cloud-native', 'container escape'], 'Cloud Security'),
    (['data breach', ' breach', 'data leak', 'stolen data', 'data exposure', 'leaked database'], 'Data Breach'),
    (['ddos', 'denial of service', 'amplification attack'], 'DDoS'),
    (['artificial intelligence', ' llm ', 'deepfake', 'generative ai', 'ai-powered attack', 'chatgpt attack'], 'AI / ML Threats'),
    (['identity', ' iam ', 'mfa bypass', 'active directory', 'kerberos', 'privilege escalation'], 'Identity & Access'),
    (['android', ' ios ', 'mobile malware', 'iphone hack', 'smartphone'], 'Mobile Security'),
]


def detect_sector(title: str, description: str, categories: list, default: str) -> str:
    text = f"{title} {description} {' '.join(categories)}".lower()
    for keywords, sector in SECTOR_KEYWORDS:
        if any(kw in text for kw in keywords):
            return sector
    if categories:
        clean = categories[0].strip().title()
        if 3 < len(clean) < 50:
            return clean
    return default


def parse_date(raw: str) -> str:
    if not raw:
        return ''
    s = raw.strip()
    # Normalize timezone words so %z can parse them
    s = re.sub(r'\b(GMT|UTC)\b', '+0000', s).strip()
    # Strip fractional seconds (e.g. .000)
    s = re.sub(r'\.\d+', '', s)
    for fmt in [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M%z',
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%d',
        '%d %b %Y %H:%M:%S %z',
        '%d %b %Y %H:%M:%S',
    ]:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            pass
    # Regex fallback — extract YYYY-MM-DD and optional HH:MM
    m = re.search(r'(\d{4}-\d{2}-\d{2})[T ]?(\d{2}:\d{2})?', raw)
    if m:
        return f"{m.group(1)} {m.group(2) or '00:00'}"
    return ''  # unrecognized — empty string sorts to end


def strip_html(text: str, maxlen: int = 280) -> str:
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', ' ', text)
    for k, v in [('&amp;','&'),('&lt;','<'),('&gt;','>'),('&quot;','"'),('&apos;',"'"),('&#39;',"'"),('&nbsp;',' ')]:
        text = text.replace(k, v)
    text = re.sub(r'&#?\w+;', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:maxlen]


def fetch_feed(feed: dict) -> list:
    cache_key  = re.sub(r'[^a-z0-9]', '_', feed['name'].lower())
    cache_file = CACHE_DIR / f'feed_{cache_key}.json'

    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text('utf-8'))
            if time.time() - data.get('_t', 0) < CACHE_TTL:
                return data.get('articles', [])
        except Exception:
            pass

    articles = []
    try:
        req = UReq(feed['url'], headers={
            'User-Agent': 'Mozilla/5.0 ThreatIntelDashboard/1.0',
            'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
        })
        with urlopen(req, timeout=15) as resp:
            raw_bytes = resp.read()

        try:
            raw = raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            raw = raw_bytes.decode('latin-1', errors='replace')

        # Strip XML declaration and collapse namespaces so ElementTree can parse cleanly
        raw = re.sub(r'<\?xml[^>]*\?>\s*', '', raw)
        raw = re.sub(r' xmlns(?::\w+)?="[^"]*"', '', raw)
        raw = re.sub(r'<(\w+):(\w+)',  lambda m: f'<{m.group(2)}',  raw)
        raw = re.sub(r'</(\w+):(\w+)>', lambda m: f'</{m.group(2)}>', raw)

        root  = ET.fromstring(raw.strip())
        items = root.findall('.//item') or root.findall('.//entry')

        for item in items[:30]:
            def g(*tags):
                for tag in tags:
                    el = item.find(tag)
                    if el is not None and el.text:
                        return el.text.strip()
                return ''

            title = strip_html(g('title'), 160)
            desc  = strip_html(g('description', 'summary', 'content', 'encoded'), 300)

            link = g('link', 'guid')
            if not link:
                el = item.find('link')
                if el is not None:
                    link = el.get('href', '') or el.get('url', '')

            pub   = parse_date(g('pubDate', 'published', 'updated', 'date'))
            cats  = [c.text.strip() for c in item.findall('category') if c.text and c.text.strip()]
            sector = detect_sector(title, desc, cats, feed['default_sector'])

            if title:
                articles.append({
                    'title':       title,
                    'description': desc,
                    'link':        link or '',
                    'pubDate':     pub,
                    'source':      feed['name'],
                    'sector':      sector,
                })

    except Exception:
        # On error try to return stale cache rather than empty
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text('utf-8'))
                return data.get('articles', [])
            except Exception:
                pass

    if articles:
        try:
            cache_file.write_text(
                json.dumps({'_t': time.time(), 'articles': articles}, ensure_ascii=False), 'utf-8'
            )
        except Exception:
            pass

    return articles


_lock  = threading.Lock()
_cache = {'data': [], 'last': 0.0, 'status': {}}


def get_all_articles(force: bool = False):
    with _lock:
        if not force and time.time() - _cache['last'] < CACHE_TTL:
            return _cache['data'], _cache['status']

    results = {}
    status  = {}

    def worker(feed, idx):
        t0   = time.time()
        arts = fetch_feed(feed)
        results[idx] = arts
        status[feed['name']] = {'count': len(arts), 'elapsed': round(time.time() - t0, 2), 'ok': len(arts) > 0}

    threads = [threading.Thread(target=worker, args=(f, i)) for i, f in enumerate(FEEDS)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=20)

    all_articles = []
    for i in range(len(FEEDS)):
        all_articles.extend(results.get(i, []))

    all_articles.sort(key=lambda a: a.get('pubDate', '') or '', reverse=True)

    with _lock:
        _cache['data']   = all_articles
        _cache['last']   = time.time()
        _cache['status'] = status

    return all_articles, status


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] {fmt % args}')

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path):
        if not path.exists():
            self.send_response(404)
            self.end_headers()
            return
        ct = {
            '.html': 'text/html; charset=utf-8',
            '.css':  'text/css',
            '.js':   'application/javascript',
            '.json': 'application/json',
        }.get(path.suffix, 'application/octet-stream')
        body = path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = urlparse(self.path).path

        if p == '/api/feeds':
            arts, status = get_all_articles()
            sectors = sorted(set(a['sector'] for a in arts))
            sources = sorted(set(a['source'] for a in arts))
            self.send_json({
                'articles':       arts,
                'count':          len(arts),
                'sectors':        sectors,
                'sources':        sources,
                'sources_status': status,
                'last_updated':   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            })

        elif p == '/api/refresh':
            arts, status = get_all_articles(force=True)
            self.send_json({
                'ok':          True,
                'count':       len(arts),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            })

        elif p in ('/', '/index.html'):
            self.send_file(Path(__file__).parent / 'index.html')

        elif p.startswith('/js/') or p.startswith('/css/'):
            self.send_file(Path(__file__).parent / p.lstrip('/'))

        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.end_headers()


if __name__ == '__main__':
    print(f'🛡️  Threat Intel Dashboard')
    print(f'   URL   : http://localhost:{PORT}')
    print(f'   Feeds : {len(FEEDS)} sources configured')
    print(f'   Cache : {CACHE_TTL // 60} min TTL  →  {CACHE_DIR}')
    print()
    print('   Pre-fetching feeds in background...')
    threading.Thread(target=lambda: get_all_articles(), daemon=True).start()
    HTTPServer(('', PORT), Handler).serve_forever()
