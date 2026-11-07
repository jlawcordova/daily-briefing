#!/usr/bin/env bash
# Installs the Pixpocket this repo pins (.pixpocket-version) into .tools/pixpocket/,
# from its GitHub release (pixpocket/pixpocket is private, so through `gh`),
# checked against the release's SHA256SUMS. The art's scripts (art/kit/program.py)
# run that copy. Run it again after changing .pixpocket-version.
set -euo pipefail
cd "$(dirname "$0")/.."
version="$(tr -d '[:space:]' < .pixpocket-version)"
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) platform=darwin-arm64 ;;
  Linux-x86_64) platform=linux-x64 ;;
  *) echo "No Pixpocket build for $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac
dest=.tools/pixpocket
if [ -x "$dest/pixpocket" ] && [ "$("$dest/pixpocket" --version)" = "pixpocket $version" ]; then
  echo "pixpocket $version is installed in $dest"; exit 0
fi
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
asset="pixpocket-$platform.tar.gz"
gh release download "v$version" -R pixpocket/pixpocket -p "$asset" -p SHA256SUMS -D "$tmp"
(cd "$tmp" && grep " $asset\$" SHA256SUMS | shasum -a 256 -c -)
mkdir -p "$tmp/x" && tar -xzf "$tmp/$asset" -C "$tmp/x"
bin="$(find "$tmp/x" -type f -name pixpocket -perm -u+x | head -1)"
[ -n "$bin" ] || { echo "No pixpocket program in $asset" >&2; exit 1; }
rm -rf "$dest" && mkdir -p "$dest" && cp "$bin" "$dest/pixpocket"
"$dest/pixpocket" --version
