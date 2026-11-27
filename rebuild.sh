#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

dpkg-scanpackages --multiversion debs /dev/null > Packages
# POCKET DEPICTION INTEGRATION
python3 <<'DEPICTION'
from pathlib import Path

p = Path("Packages")
blocks = p.read_text().strip().split("\n\n")
base = "https://r-moments.github.io/repo/"

for i, block in enumerate(blocks):
    lines = block.splitlines()
    if "Package: ru.r-moments.pocket-ipad" in lines:
        lines = [line for line in lines
                 if not line.startswith(("Depiction:", "Icon:"))]
        lines.append("Depiction: " + base +
                     "depictions/ru.r-moments.pocket-ipad/index.html")
        lines.append("Icon: " + base +
                     "depictions/ru.r-moments.pocket-ipad/Icon.png")
        blocks[i] = "\n".join(lines)

p.write_text("\n\n".join(blocks) + "\n\n")
DEPICTION

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
