(function () {
  "use strict";
  var SUPER = "Newsletter A", STAY = "Newsletter B";
  var $ = function (id) { return document.getElementById(id); };

  var days = [];          // [{day, count}] newest first
  var cache = {};         // day -> cards
  var dayIdx = 0, source = "All";

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function get(url) { return fetch(url, { cache: "no-store" }).then(function (r) { return r.json(); }); }
  function pad2(n) { return (n < 10 ? "0" : "") + n; }
  function dateOf(day) { return new Date(day + "T12:00:00"); }
  function safeUrl(u) {
    try { var p = new URL(u); return (p.protocol === "https:" || p.protocol === "http:") ? p.href : null; } catch (e) { return null; }
  }
  function store(key, val) { try { localStorage.setItem(key, val); } catch (e) {} }

  // ---------- theme ----------
  function systemDark() { return !!(window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches); }
  function isDark() {
    var t = document.documentElement.getAttribute("data-theme");
    return t ? t === "dark" : systemDark();
  }
  function paintTheme() { $("theme").textContent = isDark() ? "☼ Light mode" : "☾ Dark mode"; }
  $("theme").onclick = function () {
    var next = isDark() ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    store("digest-theme", next);
    paintTheme();
  };
  if (window.matchMedia) {
    var mq = matchMedia("(prefers-color-scheme: dark)");
    (mq.addEventListener ? mq.addEventListener.bind(mq, "change") : mq.addListener.bind(mq))(paintTheme);
  }

  // ---------- rendering ----------
  function cards() { return cache[days[dayIdx].day] || []; }
  function inSource(c) { return source === "All" || c.sources.indexOf(source) >= 0; }

  function paintDays() {
    var nav = $("days");
    nav.textContent = "";
    days.forEach(function (d, i) {
      var dt = dateOf(d.day);
      var b = el("button", "day");
      b.type = "button";
      b.setAttribute("aria-pressed", i === dayIdx ? "true" : "false");
      b.setAttribute("aria-label", dt.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" }) + ", " + d.count + " stories");
      b.appendChild(el("span", "dow", dt.toLocaleDateString("en-US", { weekday: "short" })));
      b.appendChild(el("span", "dom", String(dt.getDate())));
      b.appendChild(el("span", "cnt", String(d.count)));
      b.onclick = function () { setDay(i); };
      nav.appendChild(b);
    });
    var on = nav.querySelector('[aria-pressed="true"]');
    if (on && nav.scrollWidth > nav.clientWidth) nav.scrollLeft = Math.max(0, on.offsetLeft - nav.clientWidth / 2 + on.offsetWidth / 2);
  }

  function paintHead() {
    var d = days[dayIdx], list = cards();
    $("dayname").textContent = dateOf(d.day).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
    var shown = list.filter(inSource).length;
    var from = [SUPER, STAY].filter(function (n) { return list.some(function (c) { return c.sources.indexOf(n) >= 0; }); });
    $("daymeta").textContent = (source === "All" ? list.length : shown + " of " + list.length) + (list.length === 1 ? " story" : " stories") +
      (from.length ? " from " + from.join(" and ") : "");
    var box = $("filters");
    box.textContent = "";
    ["All", SUPER, STAY].forEach(function (name) {
      var n = name === "All" ? list.length : list.filter(function (c) { return c.sources.indexOf(name) >= 0; }).length;
      var b = el("button", "chip");
      b.type = "button";
      b.setAttribute("aria-pressed", name === source ? "true" : "false");
      b.appendChild(el("span", null, name));
      b.appendChild(el("b", null, String(n)));
      b.onclick = function () { source = name; paintHead(); paintCards(); };
      box.appendChild(b);
    });
  }

  var cardEls = [];

  function paintAllBtn() {
    var open = cardEls.filter(function (c) { return c.classList.contains("open"); }).length;
    $("all").hidden = !cardEls.length;
    $("all").textContent = cardEls.length && open === cardEls.length ? "Collapse all" : "Expand all";
  }

  function setOpen(card, open) {
    card.classList.toggle("open", open);
    card.querySelector(".toggle").setAttribute("aria-expanded", open ? "true" : "false");
  }

  function paintCards() {
    var box = $("cards"), list = cards(), shown = 0;
    box.textContent = "";
    cardEls = [];
    list.forEach(function (c, i) {
      if (!inSource(c)) return;
      var card = el("article", "card");
      card.style.setProperty("--i", String(Math.min(shown, 14)));
      var h = el("h3");
      var btn = el("button", "toggle");
      btn.type = "button";
      btn.setAttribute("aria-expanded", "false");
      btn.appendChild(el("span", "num", pad2(i + 1)));
      btn.appendChild(el("span", "title", c.headline));
      var srcs = el("span", "srcs");
      c.sources.forEach(function (s) { srcs.appendChild(el("span", "tag2", s)); });
      btn.appendChild(srcs);
      btn.appendChild(el("span", "chev"));
      h.appendChild(btn);
      card.appendChild(h);
      var panel = el("div", "panel"), inner = el("div");
      var body = el("div", "cbody");
      String(c.paragraph || "").split(/\n{2,}/).forEach(function (t) { t = t.trim(); if (t) body.appendChild(el("p", null, t)); });
      inner.appendChild(body);
      var href = c.url && safeUrl(c.url);
      if (href) {
        var a = el("a", "go", "Read the source \u2197");
        a.href = href; a.target = "_blank"; a.rel = "noopener noreferrer";
        inner.appendChild(a);
      }
      panel.appendChild(inner);
      card.appendChild(panel);
      btn.onclick = function () { setOpen(card, !card.classList.contains("open")); paintAllBtn(); };
      box.appendChild(card);
      cardEls.push(card);
      shown++;
    });
    var empty = $("empty");
    empty.hidden = shown > 0;
    if (!shown) empty.textContent = list.length ? "No stories from this newsletter on this day." : "No stories for this day.";
    paintAllBtn();
  }

  $("all").onclick = function () {
    var open = $("all").textContent === "Expand all";
    cardEls.forEach(function (c) { setOpen(c, open); });
    paintAllBtn();
  };

  function setDay(i, keepScroll) {
    if (i < 0 || i >= days.length) return;
    var d = days[i].day;
    dayIdx = i; source = "All";
    paintDays();
    var go = function () {
      if (days[dayIdx].day !== d) return;
      paintHead(); paintCards();
      if (!keepScroll) {   // if the reader had scrolled into the previous day, bring the new day's heading into view
        var bar = document.querySelector(".daybar").offsetHeight, top = $("dayhead").getBoundingClientRect().top;
        if (top < bar) window.scrollBy({ top: top - bar - 8, behavior: "auto" });
      }
    };
    if (cache[d]) return go();
    get("api/day?d=" + encodeURIComponent(d)).then(function (data) { cache[d] = data.cards; go(); });
  }

  document.addEventListener("keydown", function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.key === "ArrowRight") setDay(Math.min(days.length - 1, dayIdx + 1));
    else if (e.key === "ArrowLeft") setDay(Math.max(0, dayIdx - 1));
  });

  // ---------- start ----------
  paintTheme();
  Promise.all([get("api/days"), get("api/status")]).then(function (r) {
    days = r[0].days;
    var st = r[1].last_run;
    if (st && !st.ok) {
      var b = $("banner");
      b.hidden = false;
      b.textContent = "The last update had a problem and will retry at the next run. " + st.note;
    }
    if (!days.length) {
      $("dayname").textContent = "No digest yet";
      $("empty").hidden = false;
      $("empty").textContent = "The first digest is built at 12:00 PM Central.";
      return;
    }
    setDay(0, true);
  }).catch(function () {
    $("empty").hidden = false;
    $("empty").textContent = "Could not load the digest.";
  });
})();
