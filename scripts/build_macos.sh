#!/bin/sh

set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
machine_arch=$(uname -m)
case "$machine_arch" in
  arm64) artifact_arch="arm64" ;;
  x86_64) artifact_arch="x86_64" ;;
  *) printf '不支持的 macOS 架构：%s\n' "$machine_arch" >&2; exit 1 ;;
esac

build_root="$project_root/build/macos-$artifact_arch"
dist_root="$project_root/dist-release/macos-$artifact_arch"
release_root="$project_root/dist-release"
app_name="Labelme JSON Converter"
app_path="$dist_root/$app_name.app"
archive_path="$release_root/Labelme-JSON-Converter-macOS-$artifact_arch.zip"
app_version=$(PYTHONPATH="$project_root/src" python3 -c 'from labelme_json_converter import __version__; print(__version__)')

mkdir -p "$build_root/spec" "$build_root/work" "$build_root/config" "$dist_root"
export PYINSTALLER_CONFIG_DIR="$build_root/config"
export PYTHONPATH="$project_root/src"

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --target-arch "$artifact_arch" \
  --name "$app_name" \
  --osx-bundle-identifier "com.labelme-json-converter.app" \
  --distpath "$dist_root" \
  --workpath "$build_root/work" \
  --specpath "$build_root/spec" \
  "$project_root/packaging/launcher.py"

plutil -replace CFBundleShortVersionString -string "$app_version" "$app_path/Contents/Info.plist"
if ! plutil -replace CFBundleVersion -string "$app_version" "$app_path/Contents/Info.plist" 2>/dev/null; then
  plutil -insert CFBundleVersion -string "$app_version" "$app_path/Contents/Info.plist"
fi
codesign --force --deep --sign - "$app_path"

"$app_path/Contents/MacOS/$app_name" --self-test
"$app_path/Contents/MacOS/$app_name" --ui-smoke-test
codesign --verify --deep --strict "$app_path"
file "$app_path/Contents/MacOS/$app_name" | grep "$artifact_arch" >/dev/null

rm -f "$archive_path"
(
  cd "$dist_root"
  COPYFILE_DISABLE=1 zip -q -r -y "$archive_path" "$app_name.app"
)
unzip -t "$archive_path" >/dev/null
if unzip -Z1 "$archive_path" | grep -E '(^|/)\._|^__MACOSX/' >/dev/null; then
  printf '%s\n' 'macOS ZIP 中出现了不应发布的 Finder/AppleDouble 元数据。' >&2
  exit 1
fi
printf 'macOS 成品：%s\n' "$archive_path"
