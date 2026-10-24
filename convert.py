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

# ===== অটো ক্যাটাগরি =====
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

def detect_category(name):
    low = name.lower()
    for cat, keys in CATEGORIES:
        for k in keys:
            if k in low:
                return cat
    return "Entertainment"

# ===== প্রক্সি ডিটেক্ট (বাদ দেওয়ার জন্য নয়, হেডার ঠিক করার জন্য) =====
def is_proxy_url(url):
    u = url.lower()
    return any(p in u for p in [
        "robitv.com/rn/", "footfytv.pro/proxy/", "herokuapp.com/https://",
        "warm-caverns-", "workers.dev/", "/proxy?", "proxy/direct",
    ])

# ===== টোকেন 만료 চেক =====
def token_expired(url):
    m = re.search(r'[?&]e=(\d+)', url)
    return bool(m) and int(m.group(1)) < time.time()

# ===== সেশন প্যারামিটার =====
def has_session_param(url):
    return "nimblesessionid" in url.lower()

# ===== Working check (প্রক্সি সহ) =====
def is_working(url):
    if not url or ".m3u" not in url.lower():
        return False

    # 만료 টোকেন বাদ (প্রক্সি নয়, শুধু টোকেন)
    if token_expired(url):
        return False

    # সেশন প্যারামিটার বাদ
    if has_session_param(url):
        return False

    # প্রক্সি হলে বেশি timeout + Referer/Origin
    if is_proxy_url(url):
        timeout = 12
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.google.com/",
            "Origin": "https://www.google.com",
            "Accept": "*/*",
        }
    else:
        timeout = 5
        headers = {"User-Agent": "Mozilla/5.0"}

    # HEAD চেষ্টা
    try:
        req = urllib.request.Request(url, method="HEAD", headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status == 200:
                return True
    except Exception:
        pass

    # GET fallback (Range)
    try:
        h = dict(headers)
        h["Range"] = "bytes=0-4096"
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status in (200, 206):
                body = r.read(4096).decode("utf-8", errors="ignore")
                return ("#EXTM3U" in body or "#EXTINF" in body
                        or ".ts" in body or "mpegurl" in body.lower())
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

# ===== working check (parallel) =====
urls = [ch["url"] for ch in all_channels]
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    results = dict(zip(urls, ex.map(is_working, urls)))

working = [ch for ch in all_channels if results.get(ch["url"], False)]
skipped = [ch["name"] for ch in all_channels if not results.get(ch["url"], False)]

# ===== গ্রুপিং =====
grouped = {}
for ch in working:
    name = ch["name"]
    logo = ch.get("image", "")
    url = ch["url"]
    cat = ch.get("group") or detect_category(name)
    grouped.setdefault(cat, []).append((name, logo, url))

total = sum(len(v) for v in grouped.values())

# ===== হেডার =====
now = datetime.now(timezone.utc)
lines = [
    "#EXTM3U",
    f"#PLAYLIST:{PLAYLIST_NAME}",
    f"# Generated By: {AUTHOR}",
    f"# Facebook: {FB}",
    f"# Date: {now.strftime('%Y-%m-%d')}",
    f"# Time: {now.strftime('%H:%M UTC')}",
    f"# Total Channels: {total + 1}",
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

# ===== ক্যাটাগরি =====
order = ["Sports", "News", "Movies", "Music", "Kids", "Documentary", "Religious", "Entertainment"]
for cat in list(grouped.keys()):
    if cat not in order:
        order.append(cat)

for cat in order:
    if cat not in grouped:
        continue
    lines.append(f'#EXTINF:-1 tvg-id="header.{cat.lower()}" tvg-name="=== {cat} ===" group-title="{cat}",🔹 {cat} Channels')
    lines.append("")
    for name, logo, url in grouped[cat]:
        tid = name.lower().replace(" ", ".").replace("+", "plus")
        lines.append(f'#EXTINF:-1 tvg-id="{tid}" tvg-name="{name}" tvg-logo="{logo}" group-title="{cat}",{name}')
        lines.append(url)

# ===== ফুটার =====
lines.append("")
lines.append(f'#EXTINF:-1 tvg-id="info.madeby" tvg-name="Made by {AUTHOR}" group-title="INFO",❤ Made by {AUTHOR}')
lines.append("")

# ===== লিখুন =====
os.makedirs(OUT_DIR, exist_ok=True)
with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"✅ Working: {total} + 1 fixed = {total + 1}")
print(f"⏭ Skipped: {len(skipped)}")
