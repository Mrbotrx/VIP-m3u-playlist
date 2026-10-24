import json, os, urllib.request, concurrent.futures

JSON_URL = os.environ["JSON_API_URL"]
OUT_DIR = "Vip playlists"
OUT_FILE = os.path.join(OUT_DIR, "vip_kbpro.m3u8")

AUTHOR = "Kallyan Biswas"
FB = "www.Facebook.com/kallyan.biswas.29"

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

# ===== FAST ফিল্টার (URL গঠন) =====
FAST_KEYWORDS = ["/live", "index.m3u8", "playlist.m3u8", "chunks.m3u8", "mono.m3u8", "master.m3u8"]
SLOW_KEYWORDS = [".mp4", ".smil", ".m3u?", "tracks-v1a1/mono.ts"]

def is_fast(url):
    if not url:
        return False
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

# ===== Working check (HEAD) =====
def is_working(url):
    try:
        req = urllib.request.Request(
            url, method="HEAD",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            return r.status == 200
    except Exception:
        # HEAD fail হলে GET দিয়ে চেষ্টা
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-1024"}
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                return r.status in (200, 206)
        except Exception:
            return False

# ===== JSON আনুন =====
req = urllib.request.Request(JSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

# ===== ধাপ ১: URL গঠন ফিল্টার =====
candidates = []
skipped_fmt = []
for ch in data:
    url = ch.get("url", "")
    if not is_fast(url):
        skipped_fmt.append(ch.get("name", "Unknown"))
        continue
    candidates.append(ch)

# ===== ধাপ ২: working check (parallel) =====
urls = [ch["url"] for ch in candidates]
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    results = dict(zip(urls, ex.map(is_working, urls)))

working = [ch for ch in candidates if results.get(ch["url"], False)]
skipped_dead = [ch["name"] for ch in candidates if not results.get(ch["url"], False)]

# ===== গ্রুপিং =====
grouped = {}
for ch in working:
    name = ch.get("name", "Unknown")
    logo = ch.get("image", "")
    url = ch.get("url", "")
    cat = detect_category(name)
    grouped.setdefault(cat, []).append((name, logo, url))

# ===== হেডার =====
lines = [
    "#EXTM3U",
    f'#EXTINF:-1 tvg-name="--- {AUTHOR} ---" group-title="INFO",📺 {AUTHOR} Presents',
    "",
    f'#EXTINF:-1 tvg-name="Facebook" tvg-logo="https://cdn-icons-png.flaticon.com/512/733/733547.png" group-title="INFO",📘 {FB}',
    "",
    f'#EXTINF:-1 tvg-name="Total Channels" group-title="INFO",📊 Working: {sum(len(v) for v in grouped.values())} / Dead: {len(skipped_dead)} / Format: {len(skipped_fmt)}',
    "",
]

order = ["Sports", "News", "Movies", "Music", "Kids", "Documentary", "Religious", "Entertainment"]
for cat in order:
    if cat not in grouped:
        continue
    lines.append(f'#EXTINF:-1 tvg-name="=== {cat} ===" group-title="{cat}",🔹 {cat} Channels')
    lines.append("")
    for name, logo, url in grouped[cat]:
        lines.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{cat}",{name}')
        lines.append(url)

lines.append("")
lines.append(f'#EXTINF:-1 tvg-name="Made by {AUTHOR}" group-title="INFO",❤ Made by {AUTHOR}')
lines.append("")

os.makedirs(OUT_DIR, exist_ok=True)
with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

total = sum(len(v) for v in grouped.values())
print(f"✅ Working: {total}")
print(f"⏭ Format-skipped: {len(skipped_fmt)}")
print(f"⏭ Dead-skipped: {len(skipped_dead)}")
if skipped_dead:
    print("   Dead:", ", ".join(skipped_dead[:10]), "..." if len(skipped_dead) > 10 else "")
