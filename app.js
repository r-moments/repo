var lang = "ru";
var theme = "dark";

try {
    lang = localStorage.getItem("rm-lang") || "ru";
    theme = localStorage.getItem("rm-theme") || "dark";
} catch(e) {}

function save(key, value) {
    try { localStorage.setItem(key, value); } catch(e) {}
}

function applyTheme() {
    document.body.className = theme === "light" ? "light" : "";
    document.getElementById("theme").innerHTML =
        theme === "light" ? "&#9790;" : "&#9728;";
}

function toggleTheme() {
    theme = theme === "dark" ? "light" : "dark";
    save("rm-theme", theme);
    applyTheme();
}

function applyLanguage() {
    document.documentElement.lang = lang;
    var nodes = document.querySelectorAll("[data-ru]");
    for(var i=0;i<nodes.length;i++){
        nodes[i].textContent = nodes[i].getAttribute("data-"+lang);
    }
    renderPackages();
}

function toggleLanguage() {
    lang = lang === "ru" ? "en" : "ru";
    save("rm-lang", lang);
    applyLanguage();
}

function copyURL() {
    var input = document.getElementById("repoURL");
    input.focus();
    input.select();
    var copied = false;
    try { copied = document.execCommand("copy"); } catch(e) {}
    alert(copied ?
        (lang === "ru" ? "Адрес скопирован" : "Address copied") :
        (lang === "ru" ? "Скопируйте выделенный адрес" : "Copy the selected address"));
}

function renderPackages() {
    var root = document.getElementById("packages");
    root.innerHTML = "";
    var items = window.RM_PACKAGES || [];

    if(!items.length){
        root.textContent = lang === "ru" ?
            "Приложения появятся здесь после публикации." :
            "Applications will appear here after publication.";
        return;
    }

    for(var i=0;i<items.length;i++){
        var p = items[i];
        var box = document.createElement("div");
        box.className = "package";

        var name = document.createElement("strong");
        name.textContent = p.Name || p.Package;
        box.appendChild(name);

        var version = document.createElement("small");
        version.textContent = p.Version + " | " + p.Architecture;
        box.appendChild(version);

        var desc = document.createElement("p");
        desc.textContent = p.Description || "";
        box.appendChild(desc);

        var link = document.createElement("a");
        link.href = p.Filename;
        link.textContent = lang === "ru" ? "Скачать DEB" : "Download DEB";
        box.appendChild(link);
        root.appendChild(box);
    }
}

applyTheme();
applyLanguage();
