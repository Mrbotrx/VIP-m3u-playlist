import json, os, urllib.request

# ===== JSON URL Secret থেকে আসবে, কোডে নেই =====
JSON_URL = os.environ["JSON_API_URL"]

OUT_DIR = "Vip playlists"
OUT_FILE = os.path.join(OUT_DIR, "vip_kbpro.m3u8")

# ===== ক্রেডিট =====
AUTHOR = "Kallyan Biswas"
FB = "www.Facebook.com/kallyan.bisws.29"

# ===== অটো ক্যাটাগরি কীওয়ার্ড =====
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

# ===== ফিল্টার: শুধু .m3u8 রাখুন =====
def is_m3u8(url):
    return bool(url) and ".m3u8" in url.lower()

# ===== JSON আনুন =====
req = urllib.request.Request(JSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

# ===== গ্রুপিং =====
grouped = {}
skipped = []
for ch in data:
    name = ch.get("name", "Unknown")
    logo = ch.get("image", "")
    url = ch.get("url", "")
    if not is_m3u8(url):
        skipped.append(name)
        continue
    cat = detect_category(name)
    grouped.setdefault(cat, []).append((name, logo, url))

# ===== হেডার =====
lines = [
    "#EXTM3U",
    f'#EXTINF:-1 tvg-name="--- {AUTHOR} ---" group-title="INFO",📺 {AUTHOR} Presents',
    "",
    f'#EXTINF:-1 tvg-name="Facebook" tvg-logo="https://cdn-icons-png.flaticon.com/512/733/733547.png" group-title="INFO",📘 {FB}',
    "",
    f'#EXTINF:-1 tvg-name="Total Channels" group-title="INFO",📊 Working: {sum(len(v) for v in grouped.values())} / Skipped: {len(skipped)}',
    "",
]

# ===== ক্যাটাগরি আউটপুট =====
order = ["Sports", "News", "Movies", "Music", "Kids", "Documentary", "Religious", "Entertainment"]
for cat in order:
    if cat not in grouped:
        continue
    lines.append(f'#EXTINF:-1 tvg-name="=== {cat} ===" group-title="{cat}",🔹 {cat} Channels')
    lines.append("")
    for name, logo, url in grouped[cat]:
        lines.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{cat}",{name}')
        lines.append(url)

# ===== ফুটার =====
lines.append("")
lines.append(f'#EXTINF:-1 tvg-name="Made by {AUTHOR}" group-title="INFO",❤ Made by {AUTHOR}')
lines.append("")

# ===== লিখুন =====
os.makedirs(OUT_DIR, exist_ok=True)
with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

total = sum(len(v) for v in grouped.values())
print(f"✅ Working: {total} | Skipped: {len(skipped)}")
if skipped:
    print("⏭ Skipped:", ", ".join(skipped[:10]), "..." if len(skipped) > 10 else "")
