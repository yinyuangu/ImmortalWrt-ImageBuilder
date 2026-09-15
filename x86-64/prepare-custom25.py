#!/usr/bin/env python3
"""Fetch only selected APKs; never execute third-party .run installers."""
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import time
import urllib.request

OUT = Path("custom25-apks")
OUT.mkdir(exist_ok=True)
REV = "1244f9bd12a74747d7707bca504577c8ddf83ed5"
BASE = f"https://raw.githubusercontent.com/wukongdaily/apk/{REV}/run/x86/"
records = []


def fetch(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                return response.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def save(name, data, source):
    (OUT / name).write_bytes(data)
    records.append({"file": name, "sha256": hashlib.sha256(data).hexdigest(), "source": source})


for path in (
    "lucky/luci-app-lucky-3.0.3-r15.apk",
    "lucky/luci-i18n-lucky-zh-cn-26.021.55893~28c17bc.apk",
    "lucky/lucky-2.27.2-r1.apk",
    "partexp/luci-app-partexp-2.0.5-r20260318.apk",
    "partexp/luci-i18n-partexp-zh-cn-25.355.34625~38e15b6.apk",
):
    save(Path(path).name, fetch(BASE + path), BASE + path)

url = BASE + "25-mosdns_v5.3.4-r5_x86_64.run"
data = fetch(url)
skip = int(re.search(rb'^skip="(\d+)"$', data[:30000], re.M).group(1))
payload = data.split(b"\n", skip)[skip]
wanted = {
    "luci-app-mosdns-1.7.4-r1.apk",
    "luci-i18n-mosdns-zh-cn-26.157.32907~65060f7.apk",
    "mosdns-5.3.4-r5.apk",
    "v2dat-2022.12.15~47b8ee51-r4.apk",
}
found = set()
with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
    for member in archive.getmembers():
        name = Path(member.name).name
        if member.isfile() and name in wanted:
            save(name, archive.extractfile(member).read(), url)
            found.add(name)
assert found == wanted, f"Missing MosDNS packages: {wanted - found}"

# OpenClash bundles its Chinese LMO files in the main package.
release = json.loads(fetch("https://api.github.com/repos/vernesong/OpenClash/releases/latest"))
assets = [a for a in release["assets"] if a["name"].endswith(".apk")]
assert len(assets) == 1, "Expected exactly one upstream OpenClash APK"
asset = assets[0]
save(asset["name"], fetch(asset["browser_download_url"]), asset["browser_download_url"])
Path("custom25-sources.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(records, indent=2))
