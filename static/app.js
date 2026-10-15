(function () {
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  // remember chosen language when user clicks a language link
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest("a[hreflang], .lang-card");
    if (a) store("lang", a.getAttribute("data-l") || (a.getAttribute("hreflang") || "").toLowerCase());
  });

  // copy promo code
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest && ev.target.closest(".copy");
    if (!b) return;
    var code = b.getAttribute("data-code"), label = b.textContent;
    function done() { b.textContent = b.getAttribute("data-done"); b.classList.add("done");
      setTimeout(function () { b.textContent = label; b.classList.remove("done"); }, 1600); }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(code).then(done, fallback);
    else fallback();
    function fallback() { var t = document.createElement("textarea"); t.value = code; document.body.appendChild(t);
      t.select(); try { document.execCommand("copy"); } catch (e) {} t.remove(); done(); }
  });

  // mobile menu
  var burger = document.getElementById("burger"), mnav = document.getElementById("mainnav");
  if (burger && mnav) burger.addEventListener("click", function () {
    var open = mnav.classList.toggle("open"); burger.setAttribute("aria-expanded", open ? "true" : "false");
  });

  // close language dropdown on outside click
  document.addEventListener("click", function (ev) {
    document.querySelectorAll("details.langs[open]").forEach(function (d) { if (!d.contains(ev.target)) d.removeAttribute("open"); });
  });

  // suggest switching to the visitor's browser language
  var body = document.body, cur = body.getAttribute("data-lang"), sug = document.getElementById("suggest");
  if (sug && cur) {
    var map = {}; try { map = JSON.parse(body.getAttribute("data-suggest") || "{}"); } catch (e) {}
    var chosen = store("lang"), dismissed = store("suggest-off");
    if (!dismissed && chosen !== cur) {
      var want = null, n = navigator.languages || [navigator.language || ""];
      for (var i = 0; i < n.length && !want; i++) {
        var c = (n[i] || "").toLowerCase(), b = c.split("-")[0];
        if (map[c]) want = c; else if (b === "pt" && map["pt-br"]) want = "pt-br"; else if (map[b]) want = b;
      }
      if (want && want !== cur) {
        sug.querySelector("span").textContent = map[want][0];
        var link = sug.querySelector("a"); link.textContent = map[want][1]; link.href = map[want][2];
        link.addEventListener("click", function () { store("lang", want); });
        sug.hidden = false;
        sug.querySelector(".x").addEventListener("click", function () { sug.hidden = true; store("suggest-off", "1"); store("lang", cur); });
      }
    }
  }

  // keep active category tab visible in the scrollable nav
  var onTab = document.querySelector(".cats a.on"), tabs = document.querySelector(".cats");
  if (onTab && tabs && tabs.scrollWidth > tabs.clientWidth) tabs.scrollLeft = onTab.offsetLeft - tabs.clientWidth / 2 + onTab.offsetWidth / 2;

  // copy promo code when the main CTA is pressed (page still opens)
  var toastEl;
  function toast(msg) {
    if (!toastEl) { toastEl = document.createElement("div"); toastEl.className = "toast"; document.body.appendChild(toastEl); }
    toastEl.textContent = msg; toastEl.classList.add("show");
    clearTimeout(toastEl._t); toastEl._t = setTimeout(function () { toastEl.classList.remove("show"); }, 2600);
  }
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest("a[data-code]");
    if (!a) return;
    var c = a.getAttribute("data-code");
    try { if (navigator.clipboard) navigator.clipboard.writeText(c); } catch (e) {}
    toast(a.getAttribute("data-msg") || c);
  });

  // mobile sticky bonus bar: show after the hero CTA scrolls out of view
  var mbar = document.getElementById("mbar"), heroCta = document.querySelector(".rhero-cta");
  if (mbar && heroCta && "IntersectionObserver" in window) {
    new IntersectionObserver(function (en) { mbar.classList.toggle("on", !en[0].isIntersecting); }).observe(heroCta);
  }

  // spotlight effect on cards
  document.addEventListener("pointermove", function (ev) {
    var c = ev.target.closest && ev.target.closest(".card");
    if (!c) return;
    var r = c.getBoundingClientRect();
    c.style.setProperty("--mx", (ev.clientX - r.left) + "px");
    c.style.setProperty("--my", (ev.clientY - r.top) + "px");
  });

  // reveal on scroll
  if ("IntersectionObserver" in window && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    var io = new IntersectionObserver(function (ents) {
      ents.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -40px 0px" });
    document.querySelectorAll(".card, .feat, .faq details, .stats div").forEach(function (el, i) {
      el.classList.add("reveal"); el.style.transitionDelay = (i % 6) * 50 + "ms"; io.observe(el);
    });
  }

  // filters, search, sorting, view toggle
  var cardsBox = document.getElementById("cards");
  if (!cardsBox) {
    var qq = document.getElementById("q"), rowsBox = document.querySelector(".tablewrap.codes tbody");
    if (qq && rowsBox) qq.addEventListener("input", function () {
      var v = qq.value.trim().toLowerCase(), n = 0;
      Array.prototype.forEach.call(rowsBox.children, function (r) {
        var ok = !v || (r.getAttribute("data-name") || "").indexOf(v) > -1; r.hidden = !ok; if (ok) n++;
      });
      document.getElementById("empty").hidden = n > 0;
    });
    return;
  }
  var tbody = document.querySelector("#table tbody"), empty = document.getElementById("empty");
  var q = document.getElementById("q");
  var feature = "";
  function apply() {
    var shown = 0, query = (q && q.value || "").trim().toLowerCase();
    [cardsBox.children, tbody.children].forEach(function (list) {
      Array.prototype.forEach.call(list, function (el) {
        var ok = (!feature || (" " + el.getAttribute("data-features") + " ").indexOf(" " + feature + " ") > -1) &&
                 (!query || (el.getAttribute("data-name") || "").indexOf(query) > -1);
        el.hidden = !ok; if (ok && list === cardsBox.children) shown++;
        if (ok) el.classList.add("in");
      });
    });
    empty.hidden = shown > 0;
  }
  if (q) q.addEventListener("input", apply);
  document.querySelectorAll(".fchip").forEach(function (b) {
    b.addEventListener("click", function () {
      document.querySelectorAll(".fchip").forEach(function (x) { x.classList.remove("on"); });
      b.classList.add("on"); feature = b.getAttribute("data-f"); apply();
    });
  });
  var sel = document.getElementById("sort");
  if (sel) sel.addEventListener("change", function () {
    var key = sel.value;
    [cardsBox, tbody].forEach(function (box) {
      Array.prototype.slice.call(box.children).sort(function (a, b) {
        var d = parseFloat(a.getAttribute("data-" + key)) - parseFloat(b.getAttribute("data-" + key));
        return d || (parseFloat(a.getAttribute("data-order")) - parseFloat(b.getAttribute("data-order")));
      }).forEach(function (el) { box.appendChild(el); });
    });
  });
  var tableBox = document.getElementById("table");
  function setView(v) {
    document.querySelectorAll(".view button").forEach(function (x) { x.classList.toggle("on", x.getAttribute("data-view") === v); });
    cardsBox.hidden = v === "table"; tableBox.hidden = v !== "table"; store("view", v);
  }
  document.querySelectorAll(".view button").forEach(function (b) {
    b.addEventListener("click", function () { setView(b.getAttribute("data-view")); });
  });
  if (store("view") === "table") setView("table");
})();
