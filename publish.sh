#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ "$#" -gt 0 ]; then
    for FILE in "$@"; do
        [ -f "$FILE" ] || { echo "Файл не найден: $FILE"; exit 1; }
        dpkg-deb --info "$FILE"
        if [ "$(stat -c%s "$FILE")" -ge 104857600 ]; then
            echo "Ошибка: DEB превышает допустимый размер GitHub."
            exit 1
        fi
        DEST="debs/$(basename "$FILE")"
        if [ -e "$DEST" ] && ! cmp -s "$FILE" "$DEST"; then
            echo "Файл уже существует. Используй новый номер версии."
            exit 1
        fi
        if [ ! -e "$DEST" ]; then
            cp "$FILE" "$DEST"
        fi
    done
fi

./rebuild.sh

git add -- .nojekyll README.md index.html style.css app.js \
    catalog.js Logo.png CydiaIcon.png Packages Packages.gz \
    Packages.bz2 Release rebuild.sh publish.sh debs depictions screenshots

if git diff --cached --quiet; then
    echo "Нет новых изменений."
else
    git commit -m "Update r.moments Repository"
fi

git push origin main

echo
echo "=== ПУБЛИКАЦИЯ ЗАВЕРШЕНА ==="
echo "https://r-moments.github.io/repo/"
