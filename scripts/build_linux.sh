#!/bin/sh

set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
machine_arch=$(uname -m)
if [ "$machine_arch" != "x86_64" ]; then
  printf 'Linux 首版只支持 x86_64，当前架构：%s\n' "$machine_arch" >&2
  exit 1
fi

build_root="$project_root/build/linux-x86_64"
dist_root="$project_root/dist-release/linux-x86_64"
release_root="$project_root/dist-release"
binary_path="$dist_root/labelme-json-converter"
archive_path="$release_root/Labelme-JSON-Converter-Linux-x86_64.zip"

mkdir -p "$build_root/spec" "$build_root/work" "$build_root/config" "$dist_root"
export PYINSTALLER_CONFIG_DIR="$build_root/config"
export PYTHONPATH="$project_root/src"

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name "labelme-json-converter" \
  --distpath "$dist_root" \
  --workpath "$build_root/work" \
  --specpath "$build_root/spec" \
  "$project_root/packaging/launcher.py"

"$binary_path" --self-test
if [ -n "${DISPLAY:-}" ]; then
  "$binary_path" --ui-smoke-test
elif command -v xvfb-run >/dev/null 2>&1; then
  xvfb-run -a "$binary_path" --ui-smoke-test
else
  printf '%s\n' '缺少 DISPLAY 和 xvfb-run，无法执行 GUI 烟雾测试。' >&2
  exit 1
fi
file "$binary_path" | grep 'ELF 64-bit.*x86-64' >/dev/null

rm -f "$archive_path"
(cd "$dist_root" && zip -q -9 "$archive_path" "labelme-json-converter")
unzip -t "$archive_path" >/dev/null
printf 'Linux 成品：%s\n' "$archive_path"

