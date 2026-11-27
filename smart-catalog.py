from pathlib import Path
import subprocess
import tempfile
import hashlib
import functools
import shutil
import json
import gzip
import bz2
import re
import os
ROOT = Path.home() / 'Desktop/Projects/Repository'
WORK = ROOT / '.manager'
PREVIEW = WORK / 'smart-preview'
BASE = 'https://r-moments.github.io/repo/'

def run(*args, cwd=ROOT):
    subprocess.run(args, cwd=cwd, check=True)

def output(*args, cwd=ROOT):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

def field(deb, key):
    return output('dpkg-deb', '-f', str(deb), key)

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()

def compare(a, b):
    for op, result in [('gt', 1), ('lt', -1)]:
        rc = subprocess.run(['dpkg', '--compare-versions', a, op, b]).returncode
        if rc == 0:
            return result
        if rc != 1:
            raise RuntimeError('Ошибка сравнения версий')
    return 0

def read_catalog(repo):
    raw = (repo / 'catalog.js').read_text().strip()
    prefix = 'window.RM_PACKAGES = '
    if not raw.startswith(prefix):
        raise RuntimeError('Неизвестный формат catalog.js')
    return json.loads(raw[len(prefix):].rstrip(';'))

def latest_packages(items):
    latest = {}
    for item in items:
        key = item['Package']
        if key not in latest or compare(item['Version'], latest[key]['Version']) > 0:
            latest[key] = item
    return sorted(latest.values(), key=lambda p: (p.get('Name', p['Package']).lower(), p['Package']))

def smart_catalog(repo):
    items = read_catalog(repo)
    latest = latest_packages(items)
    (repo / 'catalog-latest.js').write_text('window.RM_LATEST_PACKAGES = ' + json.dumps(latest, ensure_ascii=True) + ';\n')
    print('Всего версий:', len(items))
    print('Уникальных приложений:', len(latest))
    for item in latest:
        print('OK:', item['Package'], item['Version'])
    index = repo / 'index.html'
    page = index.read_text()
    if 'catalog-latest.js' not in page:
        marker = '<script src="catalog.js"></script>'
        if marker not in page:
            raise RuntimeError('Не найден catalog.js')
        page = page.replace(marker, marker + '\n<script src="catalog-latest.js"></script>', 1)
    page = re.sub('<!-- POCKET PAGE LINK -->.*?</div>', '', page, count=1, flags=re.S)
    index.write_text(page)
    app = repo / 'app.js'
    source = app.read_text()
    start = source.index('function renderPackages()')
    end = source.index('\napplyTheme();', start)
    replacement = '\nfunction renderPackages() {\n    var root = document.getElementById("packages");\n    root.innerHTML = "";\n\n    var items = window.RM_LATEST_PACKAGES ||\n                window.RM_PACKAGES || [];\n\n    if (!items.length) {\n        root.textContent = lang === "ru" ?\n            "Приложения пока отсутствуют." :\n            "No applications yet.";\n        return;\n    }\n\n    function localURL(url) {\n        var base = "https://r-moments.github.io/repo/";\n        if (url && url.indexOf(base) === 0) {\n            return url.substring(base.length);\n        }\n        return "";\n    }\n\n    for (var i = 0; i < items.length; i++) {\n        var p = items[i];\n\n        var box = document.createElement("div");\n        box.className = "package";\n\n        var iconURL = localURL(p.Icon);\n\n        if (iconURL) {\n            var icon = document.createElement("img");\n            icon.src = iconURL;\n            icon.className = "rm-package-icon";\n            icon.alt = "";\n            box.appendChild(icon);\n        }\n\n        var name = document.createElement("strong");\n        name.textContent = p.Name || p.Package;\n        box.appendChild(name);\n\n        var version = document.createElement("small");\n        version.textContent =\n            p.Version + " | " + p.Architecture;\n        box.appendChild(version);\n\n        var desc = document.createElement("p");\n        desc.textContent = p.Description || "";\n        box.appendChild(desc);\n\n        var depiction = localURL(p.Depiction);\n\n        if (depiction) {\n            var details = document.createElement("a");\n            details.href = depiction;\n            details.className = "rm-details";\n            details.textContent = lang === "ru" ?\n                "Подробнее" : "Details";\n            box.appendChild(details);\n        }\n\n        var download = document.createElement("a");\n        download.href = p.Filename;\n        download.textContent = lang === "ru" ?\n            "Скачать DEB" : "Download DEB";\n\n        box.appendChild(download);\n        root.appendChild(box);\n    }\n}\n'
    app.write_text(source[:start] + replacement + source[end:])
    css = repo / 'style.css'
    style = css.read_text()
    if 'SMART CATALOG 1.1.2' not in style:
        style += '\n/* SMART CATALOG 1.1.2 */\n\n.rm-package-icon {\n    float: left;\n    width: 64px;\n    height: 64px;\n    margin: 0 14px 12px 0;\n    border-radius: 14px;\n}\n\n.package {\n    overflow: hidden;\n}\n\n.package .rm-details {\n    display: inline-block;\n    margin-right: 14px;\n}\n\n.package small {\n    display: block;\n}\n'
        css.write_text(style)
    print('OK: Smart Catalog')
    print('OK: Auto Icon')
    print('OK: Depiction Links')

def sync_page(repo, package):
    pagefile = repo / 'depictions' / package / 'index.html'
    page = pagefile.read_text()
    if 'RM AUTO METADATA 1.1.2' in page:
        return
    script = '\n<!-- RM AUTO METADATA 1.1.2 -->\n<script src="../../catalog-latest.js"></script>\n<script>\n(function(){\n    var items = window.RM_LATEST_PACKAGES || [];\n    var packageID = PACKAGE_ID;\n\n    function put(id, value) {\n        var node = document.getElementById(id);\n        if (node) node.textContent = value;\n    }\n\n    for (var i = 0; i < items.length; i++) {\n        var p = items[i];\n\n        if (p.Package !== packageID) continue;\n\n        var version = String(p.Version);\n        var appVersion = version.replace(/^[0-9]+:/, "");\n        appVersion = appVersion.replace(/-[^-]+$/, "");\n\n        var size =\n            (Number(p.Size) / 1048576).toFixed(1) + " MiB";\n\n        put("app-version", appVersion);\n        put("package-version", version);\n        put("hero-size", size);\n        put("package-size", size);\n        break;\n    }\n})();\n</script>\n'
    script = script.replace('PACKAGE_ID', json.dumps(package))
    if '</body>' not in page:
        raise RuntimeError('Не найден конец HTML')
    pagefile.write_text(page.replace('</body>', script + '\n</body>', 1))
    print('OK: Auto Metadata', package)

def verify(repo):
    raw = (repo / 'Packages').read_bytes()
    if gzip.decompress((repo / 'Packages.gz').read_bytes()) != raw:
        raise RuntimeError('Ошибка Packages.gz')
    if bz2.decompress((repo / 'Packages.bz2').read_bytes()) != raw:
        raise RuntimeError('Ошибка Packages.bz2')
    print('OK: сжатые каталоги')
    algorithms = {'MD5Sum:': 'md5', 'SHA1:': 'sha1', 'SHA256:': 'sha256'}
    algorithm = None
    checked = set()
    for line in (repo / 'Release').read_text().splitlines():
        if line in algorithms:
            algorithm = algorithms[line]
        elif line.startswith(' ') and algorithm:
            expected, size, name = line.split()
            data = (repo / name).read_bytes()
            if len(data) != int(size):
                raise RuntimeError('Размер: ' + name)
            if hashlib.new(algorithm, data).hexdigest() != expected:
                raise RuntimeError('Хеш: ' + name)
            checked.add((algorithm, name))
        else:
            algorithm = None
    for algorithm in algorithms.values():
        for name in ('Packages', 'Packages.gz', 'Packages.bz2'):
            if (algorithm, name) not in checked:
                raise RuntimeError('Отсутствует хеш: ' + name)
    print('OK: Release MD5 / SHA1 / SHA256')
    items = read_catalog(repo)
    for p in items:
        path = (repo / p['Filename']).resolve()
        if not path.is_relative_to(repo / 'debs'):
            raise RuntimeError('Недопустимый путь')
        if not path.is_file():
            raise RuntimeError('DEB отсутствует')
        if digest(path) != p['SHA256']:
            raise RuntimeError('SHA256: ' + p['Package'])
        if path.stat().st_size != int(p['Size']):
            raise RuntimeError('Размер: ' + p['Package'])
        if field(path, 'Package') != p['Package']:
            raise RuntimeError('Package ID не совпадает')
        if field(path, 'Version') != p['Version']:
            raise RuntimeError('Version не совпадает')
        for key in ('Depiction', 'Icon'):
            url = p.get(key, '')
            if url.startswith(BASE):
                target = (repo / url[len(BASE):]).resolve()
                if not target.is_relative_to(repo):
                    raise RuntimeError('Недопустимый URL')
                if not target.is_file():
                    raise RuntimeError('Нет файла: ' + url)
        print('OK:', p['Package'], p['Version'])
    print('OK: целостность каталога')

def simulate():
    if output('git', 'status', '--porcelain'):
        raise RuntimeError('Сначала проверь локальные изменения Git')
    value = input('Путь к DEB (Enter — тест Pocket iPhone): ').strip()
    if not value:
        value = str(ROOT / 'ready-to-publish/ru.r-moments.pocket_3.76.34-3-iphone.deb')
    deb = Path(value).expanduser().resolve()
    if not deb.is_file():
        raise RuntimeError('DEB не найден')
    package = field(deb, 'Package')
    version = field(deb, 'Version')
    if not re.fullmatch('ru\\.r-moments\\.[a-z0-9.+-]+', package):
        raise RuntimeError('Неверный Package ID')
    if field(deb, 'Architecture') != 'iphoneos-arm':
        raise RuntimeError('Неверная архитектура')
    if deb.stat().st_size >= 104857600:
        raise RuntimeError('Превышен лимит GitHub')
    draft = WORK / 'preview' / package
    if not (draft / 'metadata.json').is_file():
        raise RuntimeError('Сначала подготовь страницу через 11 -> 01')
    meta = json.loads((draft / 'metadata.json').read_text())
    if meta['id'] != package or meta['version'] != version:
        raise RuntimeError('Метаданные не совпадают')
    expected_size = '%.1f MiB' % (deb.stat().st_size / 1048576)
    if meta['size'] != expected_size:
        raise RuntimeError('Размер не совпадает')
    print('\n=== SAFE PUBLISH SIMULATION ===')
    print('Package:', package)
    print('Version:', version)
    print('SHA256:', digest(deb))
    original_head = output('git', 'rev-parse', 'HEAD')
    with tempfile.TemporaryDirectory(dir=WORK) as tmp:
        stage = Path(tmp) / 'repository'
        run('git', 'clone', '--quiet', '--no-hardlinks', str(ROOT), str(stage))
        run('git', 'remote', 'remove', 'origin', cwd=stage)
        print('OK: изолированная копия без remote')
        for old in (stage / 'debs').glob('*.deb'):
            if field(old, 'Package') == package:
                if compare(version, field(old, 'Version')) <= 0:
                    raise RuntimeError('Версия не является обновлением')
        target = stage / 'debs' / deb.name
        public = stage / 'depictions' / package
        if target.exists() or public.exists():
            raise RuntimeError('Замена существующей страницы пока не разрешена')
        shutil.copy2(deb, target)
        shutil.copytree(draft, public)
        if digest(deb) != digest(target):
            raise RuntimeError('Ошибка копирования DEB')
        run('./rebuild.sh', cwd=stage)
        smart_catalog(stage)
        sync_page(stage, package)
        verify(stage)
        items = read_catalog(stage)
        if not any((p['Package'] == package and p['Version'] == version for p in items)):
            raise RuntimeError('Новый пакет не индексирован')
        assert compare('1.10', '1.9') > 0
        assert compare('1.0~beta', '1.0') < 0
        assert compare('1.0-10', '1.0-9') > 0
        test_items = [{'Package': 'test', 'Version': '1.9'}, {'Package': 'test', 'Version': '1.10'}]
        assert latest_packages(test_items)[0]['Version'] == '1.10'
        print('OK: Debian Version Engine')
        if PREVIEW.exists():
            shutil.rmtree(PREVIEW)
        shutil.copytree(stage, PREVIEW, ignore=shutil.ignore_patterns('.git'))
    if output('git', 'rev-parse', 'HEAD') != original_head:
        raise RuntimeError('Исходный HEAD изменился')
    if output('git', 'status', '--porcelain'):
        raise RuntimeError('Исходный репозиторий изменился')
    print('\n=== SIMULATION SUCCESS ===')
    print('OK: исходный репозиторий не изменён')
    print('OK: GitHub не изменён')
    print('OK: Pocket iPhone не опубликован')
    print('Предпросмотр:', PREVIEW / 'index.html')
    subprocess.Popen(['xdg-open', str(PREVIEW / 'index.html')])

def open_preview():
    page = PREVIEW / 'index.html'
    if not page.is_file():
        raise RuntimeError('Сначала выполни симуляцию')
    subprocess.Popen(['xdg-open', str(page)])

def status():
    print('\n=== SMART CATALOG STATUS ===')
    if PREVIEW.exists():
        verify(PREVIEW)
        print('Предпросмотр:', PREVIEW)
    else:
        print('Симуляция ещё не выполнялась')
    print('\n=== ОСНОВНОЙ РЕПОЗИТОРИЙ ===')
    print(output('git', 'log', '-1', '--oneline'))
    print(output('git', 'status', '--short') or 'Git clean')
    for deb in (ROOT / 'debs').glob('*.deb'):
        print(field(deb, 'Package'), field(deb, 'Version'))

if __name__ == "__main__":
    repository = Path(__file__).resolve().parent
    smart_catalog(repository)

