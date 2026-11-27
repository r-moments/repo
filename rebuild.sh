#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

dpkg-scanpackages --multiversion debs /dev/null > Packages
gzip -n -9 -c Packages > Packages.gz
bzip2 -9 -c Packages > Packages.bz2

python3 <<'PY'
import json
import hashlib
from pathlib import Path
from email.utils import formatdate

packages = []
for block in Path("Packages").read_text().split("\n\n"):
    item = {}
    for line in block.splitlines():
        if line and not line[0].isspace() and ": " in line:
            key, value = line.split(": ", 1)
            item[key] = value
    if item.get("Package"):
        packages.append(item)

Path("catalog.js").write_text(
    "window.RM_PACKAGES = " +
    json.dumps(packages, ensure_ascii=True) + ";\n"
)

release = [
    "Origin: r.moments Repository",
    "Label: r.moments",
    "Suite: stable",
    "Version: 1.0",
    "Codename: legacy",
    "Architectures: iphoneos-arm",
    "Components: main",
    "Description: Legacy iOS Applications and Tweaks",
    "Date: " + formatdate(usegmt=True)
]

files = ["Packages", "Packages.gz", "Packages.bz2"]

for label, algorithm in [
    ("MD5Sum", "md5"),
    ("SHA1", "sha1"),
    ("SHA256", "sha256")
]:
    release.append(label + ":")
    for filename in files:
        data = Path(filename).read_bytes()
        digest = hashlib.new(algorithm, data).hexdigest()
        release.append(" " + digest + " " + str(len(data)) + " " + filename)

Path("Release").write_text("\n".join(release) + "\n")
print("Packages indexed:", len(packages))
PY

echo "=== Каталог успешно обновлён ==="
