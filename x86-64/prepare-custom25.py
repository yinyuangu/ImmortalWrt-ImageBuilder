#!/usr/bin/env python3
"""Fetch only selected APKs; never execute third-party .run installers."""
import hashlib
import io
import json
from pathlib import Path
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


# Replace older frontend/core packages when reusing this profile workspace.
for pattern in ("luci-app-adguardhome-*.apk", "luci-i18n-adguardhome-zh-cn-*.apk",
                "luci-app-lucky-*.apk", "luci-i18n-lucky-zh-cn-*.apk", "lucky-*.apk"):
    for old_package in OUT.glob(pattern):
        old_package.unlink()

for repo, tag, name, digest in (
    ("terrytyc/luci-app-adguardhome", "v3.3.0-r1", "luci-app-adguardhome-3.3.0-r1.apk", "28416b0ef0c145f142a4875b90212c6ed318dd5684831fd0d1bcaa21de359b1f"),
    ("terrytyc/luci-app-adguardhome", "v3.3.0-r1", "luci-i18n-adguardhome-zh-cn-3.3.0-r1.apk", "7714b54ed506acb52ed4fcd4f7ebbde2abe3a0e0377e2767612bfe428c8942c3"),
    ("whzhni1/luci-app-lucky", "v2.0.7", "luci-app-lucky-2.0.7-r1.apk", "1f6db943170c4aca4496270bd297cbebb533c8866f4f8755bf8847e3601c668c"),
    ("whzhni1/luci-app-lucky", "v2.0.7", "luci-i18n-lucky-zh-cn-2.0.7.apk", "6d8e698df397cb2b5a6543df36be5b450c9da9d2a0ae5311149d9b8afc0cc348"),
):
    url = f"https://github.com/{repo}/releases/download/{tag}/{name}"
    data = fetch(url)
    assert hashlib.sha256(data).hexdigest() == digest, f"Release changed: {name}"
    save(name, data, url)

# The selected Lucky frontend owns its init script and UCI config. Install
# only the upstream core binary, avoiding the conflicting legacy core APK.
url = "https://github.com/gdy666/lucky/releases/download/v2.27.2/lucky_2.27.2_Linux_x86_64.tar.gz"
data = fetch(url)
assert hashlib.sha256(data).hexdigest() == "78adf3fa5e8869be0b1510cb7bcc755d57dccb13252989c8394a7207a392fe66", "Lucky archive changed"
with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
    members = [m for m in archive.getmembers() if m.isfile() and Path(m.name).name == "lucky"]
    assert len(members) == 1
    binary = archive.extractfile(members[0]).read()
target = Path("files/usr/bin/lucky")
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(binary)
target.chmod(0o755)
records.append({"file": str(target), "sha256": hashlib.sha256(binary).hexdigest(), "source": url})

for path in (
    "partexp/luci-app-partexp-2.0.5-r20260318.apk",
    "partexp/luci-i18n-partexp-zh-cn-25.355.34625~38e15b6.apk",
):
    save(Path(path).name, fetch(BASE + path), BASE + path)

# Use the upstream release for OpenWrt 25.12 / x86_64 directly.
url = "https://github.com/sbwml/luci-app-mosdns/releases/download/v5.3.4-r14/x86_64-openwrt-25.12.tar.gz"
payload = fetch(url)
assert hashlib.sha256(payload).hexdigest() == "7371d9122054fdc08b1349d300b8a5070eae24949d775fd9560656c7d4068eeb", "MosDNS release archive changed"
# Remove only this profile's previous MosDNS set when reusing a workspace.
for pattern in ("luci-app-mosdns-*.apk", "luci-i18n-mosdns-zh-cn-*.apk", "mosdns-*.apk", "v2dat-*.apk", "geo2txt-*.apk"):
    for old_package in OUT.glob(pattern):
        old_package.unlink()
wanted = {
    "luci-app-mosdns-1.7.14-r1.apk",
    "luci-i18n-mosdns-zh-cn-26.255.53985~73981c0.apk",
    "mosdns-5.3.4-r14.apk",
    "geo2txt-1.0.0-r1.apk",
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
