import json, os, urllib.request, concurrent.futures, re, time
from datetime import datetime, timezone

# ===== Secret থেকে সোর্স সংগ্রহ =====
SOURCES = []
for i in range(1, 10):
    u = os.environ.get(f"SRC_JSON_{i}", "").strip()
    if u:
        SOURCES.append({"type": "json", "url": u})
for i in range(1, 10):
    u = os.environ.get(f"SRC_M3U_{i}", "").strip()
    if u:
        SOURCES.append({"type": "m3u", "url": u})

if not SOURCES:
    print("❌ No sources found (check Secrets)")
    exit(1)

print(f"🔐 Loaded {len(SOURCES)} sources")

OUT_DIR = "Vip playlists"
OUT_FILE = os.path.join(OUT_DIR, "vip_kbpro.m3u8")

AUTHOR = "Kallyan Biswas"
FB = "www.Facebook.com/kallyan.biswas.29"
PLAYLIST_NAME = "Playlists"

# ===== সবসময় ১ম চ্যানেল =====
FIRST_CHANNEL = {
    "name": "IPTV LINKS",
    "logo": "https://raw.githubusercontent.com/Mrbotrx/Mrbotrx/refs/heads/main/IPTV_LINKS_LOGO.jpg",
    "url": "https://github.com/Mrbotrx/Mrbotrx/raw/refs/heads/main/IPTV_LINKS_VIDEO.mp4",
    "group": "IPTV",
    "tvg_id": "",
}

# ===== Auto Category System (৪ স্তর) =====

# স্তর ১: Exact Match (নির্দিষ্ট চ্যানেল নাম)
EXACT_MATCH = {
    # Sports
    "t sports": "Sports", "a sports": "Sports", "ptv sports": "Sports",
    "star sports 1": "Sports", "star sports 2": "Sports",
    "sony sports 1": "Sports", "sony sports 2": "Sports", "sony sports 5": "Sports",
    "willow sports": "Sports", "gazi tv": "Sports",
    # News
    "somoy tv": "News", "jamuna tv": "News", "ekattor hd": "News",
    "channel 24 hd": "News", "dbc news hd": "News", "atn news": "News",
    "independent tv": "News", "bangla vision": "News", "ntv": "News",
    "r tv": "News", "ekushey tv": "News", "boishakhi tv": "News",
    "channel i hd": "News", "channel 9 hd": "News", "maasranga tv": "News",
    "deepto tv hd": "News", "srk tv": "News", "star news": "News",
    "al jazeera": "News", "btv hd": "News", "bijoy tv": "News",
    "global channel hd": "News", "akhan tv": "News", "akhon tv": "News",
    # Movies
    "jalsha movies sd": "Movies", "jalsha movies hd": "Movies",
    "sony max": "Movies", "sony max 2": "Movies", "sony movies": "Movies",
    "zee bangla sonar": "Movies", "colors bangla cinema": "Movies",
    "movie bangla": "Movies",
    # Music
    "sangeet bangla": "Music", "atn music": "Music",
    "music india": "Music", "b4u music": "Music",
    # Kids
    "duronto tv": "Kids", "pogo": "Kids", "tiny pop": "Kids",
    "pbs kids": "Kids", "gopal bhar": "Kids", "moto patlu": "Kids",
    "tom and jerry": "Kids", "zb cartoon": "Kids", "batul the great": "Kids",
    # Documentary
    "animal planet": "Documentary", "discovery": "Documentary",
    # Religious
    "al quran": "Religious",
    # Entertainment
    "star jalsha hd": "Entertainment", "zee bangla": "Entertainment",
    "colors bangla": "Entertainment", "sony aath": "Entertainment",
    "enterr10": "Entertainment", "sananda tv": "Entertainment",
    "bangla plus": "Entertainment", "matribhumi tv": "Entertainment",
    "nagorik tv": "Entertainment", "asian tv": "Entertainment",
    "ananda tv": "Entertainment", "me tv": "Entertainment",
    "g-series": "Entertainment", "mohona tv": "Entertainment",
    "ayna tv": "Entertainment", "green tv": "Entertainment",
    "thikana tv": "Entertainment", "unmochon tv": "Entertainment",
}

# স্তর ২ ও ৩: নাম/গ্রুপ কীওয়ার্ড
CATEGORIES = [
    ("Sports", ["sports", "sport", "cricket", "willow", "ten ", "sony ten", "ptv", "gazi", "tsports", "a sports", "star sports"]),
    ("News", ["news", "somoy", "jamuna", "ekattor", "channel 24", "dbc", "atn news", "independent", "bangla vision", "ntv", "r tv", "ekushey", "boishakhi", "channel i", "channel 9", "maasranga", "deepto", "srk", "star news", "al jazeera", "akash", "akhan", "akhon", "btv", "bijoy", "global"]),
    ("Movies", ["movie", "cinema", "max", "jalsha movies", "sony movies", "zee bangla sonar", "colors bangla cinema"]),
    ("Music", ["music", "sangeet", "b4u", "atn music"]),
    ("Kids", ["kids", "pogo", "duronto", "gopal bhar", "tom and jerry", "motu", "batul", "tiny pop", "pbs", "cartoon", "unmochon"]),
    ("Documentary", ["discovery", "animal planet", "nat geo", "documentary"]),
    ("Religious", ["quran", "islam", "religi"]),
    ("Entertainment", []),
]

# স্তর ৪: URL কীওয়ার্ড
URL_KEYWORDS = {
    "Sports": ["/sport", "cricket", "/ten"],
    "News": ["/news"],
    "Movies": ["/movie", "/cinema"],
    "Music": ["/music"],
    "Kids": ["/kids", "/cartoon"],
    "Documentary": ["/discovery", "/documentary"],
    "Religious": ["/islam", "/quran"],
}

def detect_category(name, group="", url=""):
    # স্তর ১: Exact Match
    cat = EXACT_MATCH.get(name.lower().strip())
    if cat:
        return cat
    # স্তর ২: Group
    if group:
        low_g = group.lower()
        for cat, keys in CATEGORIES:
            for k in keys:
                if k in low_g:
                    return cat
    # স্তর ৩: নাম কীওয়ার্ড
    low_n = name.lower()
    for cat, keys in CATEGORIES:
        for k in keys:
            if k in low_n:
                return cat
    # স্তর ৪: URL
    if url:
        u = url.lower()
        for cat, keys in URL_KEYWORDS.items():
            for k in keys:
                if k in u:
                    return cat
    return "Entertainment"

# ===== Fast/Slow ক্লাসিফিকেশন =====
FAST_KEYWORDS = ["/live", "index.m3u8", "playlist.m3u8", "chunks.m3u8", "mono.m3u8", "master.m3u8"]
SLOW_KEYWORDS = [".mp4", ".smil", ".m3u?", "tracks-v1a1/mono.ts", "robitv.com/rn/", "footfytv.pro/proxy/", "herokuapp.com/https://", "warm-caverns-"]

def is_fast_url(url):
    u = url.lower()
    if ".m3u8" not in u:
        return False
    for bad in SLOW_KEYWORDS:
        if bad in u:
            return False
    for good in FAST_KEYWORDS:
        if good in u:
            return True
    return True

def token_expired(url):
    m = re.search(r'[?&]e=(\d+)', url)
    return bool(m) and int(m.group(1)) < time.time()

def has_session_param(url):
    return "nimblesessionid" in url.lower()

# ===== Working check =====
def is_working(url):
    if not url or ".m3u" not in url.lower():
        return False
    if token_expired(url) or has_session_param(url):
        return False
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status == 200:
                return True
    except Exception:
        pass
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-2048"})
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status in (200, 206):
                body = r.read(2048).decode("utf-8", errors="ignore")
                return "#EXTM3U" in body or "#EXTINF" in body or ".ts" in body
    except Exception:
        return False
    return False

# ===== JSON পার্সার =====
def parse_json_source(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        if not isinstance(data, list):
            return []
        out = []
        for ch in data:
            if not isinstance(ch, dict):
                continue
            name = ch.get("name") or ch.get("title") or "Unknown"
            logo = ch.get("image") or ch.get("logo") or ch.get("icon") or ""
            stream = ch.get("url") or ch.get("link") or ch.get("stream") or ""
            if stream:
                out.append({"name": name, "image": logo, "url": stream})
        return out
    except Exception as e:
        print(f"❌ JSON source failed: {type(e).__name__}")
        return []

# ===== M3U/M3U8 পার্সার =====
def parse_m3u_source(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"❌ M3U source failed: {type(e).__name__}")
        return []

    channels = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            name_m = re.search(r'tvg-name="([^"]*)"', line)
            logo_m = re.search(r'tvg-logo="([^"]*)"', line)
            group_m = re.search(r'group-title="([^"]*)"', line)
            comma_name = line.split(",")[-1].strip() if "," in line else ""
            name = name_m.group(1) if name_m else comma_name or "Unknown"
            logo = logo_m.group(1) if logo_m else ""
            group = group_m.group(1) if group_m else ""
            if i + 1 < len(lines):
                stream_url = lines[i + 1].strip()
                if stream_url and not stream_url.startswith("#"):
                    channels.append({"name": name, "image": logo, "url": stream_url, "group": group})
            i += 2
        else:
            i += 1
    return channels

# ===== সব সোর্স লোড =====
all_channels = []
seen = set()
seen.add(FIRST_CHANNEL["name"].lower().strip())

for idx, src in enumerate(SOURCES, 1):
    print(f"📥 Source #{idx} ({src['type']})")
    if src["type"] == "json":
        chs = parse_json_source(src["url"])
    else:
        chs = parse_m3u_source(src["url"])
    for ch in chs:
        key = ch["name"].lower().strip()
        if key in seen:
            continue
        seen.add(key)
        all_channels.append(ch)
    print(f"   → {len(chs)} channels")

print(f"📦 Total: {len(all_channels)}")

# ===== working check =====
urls = [ch["url"] for ch in all_channels]
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    results = dict(zip(urls, ex.map(is_working, urls)))

working = [ch for ch in all_channels if results.get(ch["url"], False)]

# ===== Fast / Slow ভাগ =====
fast_channels = []
slow_channels = []
for ch in working:
    if is_fast_url(ch["url"]):
        fast_channels.append(ch)
    else:
        slow_channels.append(ch)

print(f"⚡ Fast: {len(fast_channels)}")
print(f"🐢 Slow: {len(slow_channels)}")

# ===== গ্রুপিং (৪-স্তরের Auto Category) =====
fast_grouped = {}
for ch in fast_channels:
    name = ch["name"]
    logo = ch.get("image", "")
    url = ch["url"]
    group = ch.get("group", "")
    cat = detect_category(name, group, url)
    fast_grouped.setdefault(cat, []).append((name, logo, url))

slow_grouped = {}
for ch in slow_channels:
    name = ch["name"]
    logo = ch.get("image", "")
    url = ch["url"]
    group = ch.get("group", "")
    cat = detect_category(name, group, url)
    slow_grouped.setdefault(cat, []).append((name, logo, url))

total = len(fast_channels) + len(slow_channels)

# ===== হেডার =====
now = datetime.now(timezone.utc)
lines = [
    "#EXTM3U",
    f"#PLAYLIST:{PLAYLIST_NAME}",
    f"# Generated By: {AUTHOR}",
    f"# Facebook: {FB}",
    f"# Date: {now.strftime('%Y-%m-%d')}",
    f"# Time: {now.strftime('%H:%M UTC')}",
    f"# Total Channels: {total + 1} (Fast: {len(fast_channels)}, Slow: {len(slow_channels)})",
    "",
]

# ===== ১ম চ্যানেল =====
lines.append(
    f'#EXTINF:-1 tvg-id="{FIRST_CHANNEL["tvg_id"]}" '
    f'tvg-name="{FIRST_CHANNEL["name"]}" '
    f'tvg-logo="{FIRST_CHANNEL["logo"]}" '
    f'group-title="{FIRST_CHANNEL["group"]}",{FIRST_CHANNEL["name"]}'
)
lines.append(FIRST_CHANNEL["url"])
lines.append("")

# ===== FAST সেকশন =====
if fast_grouped:
    lines.append(f'#EXTINF:-1 tvg-id="header.fast" tvg-name="=== ⚡ FAST ===" group-title="FAST",⚡ Fast Channels ({len(fast_channels)})')
    lines.append("")
    order = ["Sports", "News", "Movies", "Music", "Kids", "Documentary", "Religious", "Entertainment"]
    for cat in list(fast_grouped.keys()):
        if cat not in order:
            order.append(cat)
    for cat in order:
        if cat not in fast_grouped:
            continue
        lines.append(f'#EXTINF:-1 tvg-id="header.fast.{cat.lower()}" tvg-name="=== {cat} ===" group-title="FAST {cat}",🔹 {cat}')
        lines.append("")
        for name, logo, url in fast_grouped[cat]:
            tid = name.lower().replace(" ", ".").replace("+", "plus")
            lines.append(f'#EXTINF:-1 tvg-id="{tid}" tvg-name="{name}" tvg-logo="{logo}" group-title="FAST {cat}",{name}')
            lines.append(url)

# ===== SLOW সেকশন =====
if slow_grouped:
    lines.append("")
    lines.append(f'#EXTINF:-1 tvg-id="header.slow" tvg-name="=== 🐢 SLOW ===" group-title="SLOW",🐢 Slow Channels ({len(slow_channels)})')
    lines.append("")
    order = ["Sports", "News", "Movies", "Music", "Kids", "Documentary", "Religious", "Entertainment"]
    for cat in list(slow_grouped.keys()):
        if cat not in order:
            order.append(cat)
    for cat in order:
        if cat not in slow_grouped:
            continue
        lines.append(f'#EXTINF:-1 tvg-id="header.slow.{cat.lower()}" tvg-name="=== {cat} ===" group-title="SLOW {cat}",🔹 {cat}')
        lines.append("")
        for name, logo, url in slow_grouped[cat]:
            tid = name.lower().replace(" ", ".").replace("+", "plus")
            lines.append(f'#EXTINF:-1 tvg-id="{tid}" tvg-name="{name}" tvg-logo="{logo}" group-title="SLOW {cat}",{name}')
            lines.append(url)

# ===== ফুটার =====
lines.append("")
lines.append(f'#EXTINF:-1 tvg-id="info.madeby" tvg-name="Made by {AUTHOR}" group-title="INFO",❤ Made by {AUTHOR}')
lines.append("")

# ===== লিখুন =====
os.makedirs(OUT_DIR, exist_ok=True)
with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"✅ Total: {total} + 1 fixed = {total + 1}")
print(f"   ⚡ Fast: {len(fast_channels)}")
print(f"   🐢 Slow: {len(slow_channels)}")
