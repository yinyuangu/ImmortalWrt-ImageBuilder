#!/bin/bash
set -euo pipefail
ROOT="$(pwd)"
SDK_NAME=immortalwrt-sdk-25.12.1-x86-64_gcc-14.3.0_musl.Linux-x86_64
SDK_URL="https://downloads.immortalwrt.org/releases/25.12.1/targets/x86/64/${SDK_NAME}.tar.zst"
curl --fail --location --retry 3 "$SDK_URL" -o sdk.tar.zst
echo '02ad8cfc775001ccae8e9282d19696de54e3ab3963f005737ad61f8698263edd  sdk.tar.zst' | sha256sum -c -
mkdir -p sdk
tar --zstd -xf sdk.tar.zst -C sdk --strip-components=1
cd sdk
# Pin the LuCI source to the version inspected when preparing this profile.
cp feeds.conf.default feeds.conf
sed -i '/^src-git.* luci /d' feeds.conf
printf '%s\n' 'src-git luci https://github.com/immortalwrt/luci.git^d6167ea0645cbd1327708d85f94824f42d0eb872' >> feeds.conf
./scripts/feeds update -a
./scripts/feeds install -a
# Lua and ucode headers are needed by the indirect lucihttp build.
test -e package/feeds/base/lua/Makefile
test -e package/feeds/base/ucode/Makefile || test -e package/utils/ucode/Makefile
git clone --depth 1 --branch luci https://github.com/chenmozhijin/turboacc.git turboacc-src
git -C turboacc-src fetch --depth 1 origin 530092c532839efb96e9f328d34dbf3adff4b557
git -C turboacc-src checkout 530092c532839efb96e9f328d34dbf3adff4b557
cp -a turboacc-src/luci-app-turboacc package/
# Upstream provides zh_Hans as a symlink to its legacy zh-cn directory.
test -s package/luci-app-turboacc/po/zh_Hans/turboacc.po
# SDK archives do not contain .config: generate only the requested selections.
cat > .config <<'EOF'
CONFIG_ALL=n
CONFIG_ALL_KMODS=n
CONFIG_ALL_NONSHARED=n
CONFIG_LUCI_LANG_zh_Hans=y
CONFIG_PACKAGE_luci-app-turboacc=m
CONFIG_PACKAGE_luci-app-turboacc_INCLUDE_OFFLOADING=y
CONFIG_PACKAGE_luci-app-turboacc_INCLUDE_BBR_CCA=y
CONFIG_PACKAGE_luci-app-turboacc_INCLUDE_NFT_FULLCONE=y
CONFIG_PACKAGE_luci-app-turboacc_INCLUDE_SHORTCUT_FE=n
CONFIG_PACKAGE_luci-app-turboacc_INCLUDE_SHORTCUT_FE_CM=n
CONFIG_PACKAGE_luci-app-turboacc_INCLUDE_SHORTCUT_FE_DRV=n
EOF
make defconfig
make package/luci-app-turboacc/compile V=s -j2
find bin/packages -type f \( -name 'luci-app-turboacc-*.apk' -o -name 'luci-i18n-turboacc-zh-cn-*.apk' \) -exec cp {} "$ROOT/custom25-apks/" \;
test "$(find "$ROOT/custom25-apks" -name 'luci-i18n-turboacc-zh-cn-*.apk' | wc -l)" -eq 1
