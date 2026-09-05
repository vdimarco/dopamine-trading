(function () {
  var LIVE1 = "https://lucid-tablet-tgx3.here.now/";
  var LIVE1_JS = "https://lucid-tablet-tgx3.here.now/dash.js?v=live1";
  var LOCAL_DATA = "data.json";
  var REMOTE_DATA = LIVE1 + "data.json";

  function $(id) {
    return document.getElementById(id);
  }

  function money(n) {
    if (typeof n !== "number" || !isFinite(n)) return "--";
    return n.toLocaleString(undefined, { style: "currency", currency: "USD" });
  }

  function pct(n) {
    if (typeof n !== "number" || !isFinite(n)) return "--";
    return (n >= 0 ? "+" : "") + (n * 100).toFixed(2) + "%";
  }

  function cls(n) {
    if (typeof n !== "number" || !isFinite(n) || n === 0) return "";
    return n > 0 ? "up" : "down";
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function fetchJson(url) {
    return fetch(url, { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error(url + " " + res.status);
      return res.json();
    });
  }

  function probe(url) {
    return fetch(url, { cache: "no-store" }).then(function (res) {
      return { url: url, ok: res.ok, status: res.status };
    }).catch(function () {
      return { url: url, ok: false, status: 0 };
    });
  }

  function render(snap, remote) {
    var pulse = $("pulse");
    var stale = !snap || !snap.updated_at;
    pulse.classList.toggle("stale", stale);
    $("status").textContent = stale
      ? "live1 pulse idle"
      : "live1 " + snap.updated_at + (remote ? " · remote" : " · local");
    $("equity").textContent = money(snap.equity);
    $("cash").textContent = money(snap.cash);
    $("pnl").innerHTML = '<span class="' + cls(snap.pnl) + '">' + money(snap.pnl) + "  " + pct(snap.pnl_pct) + "</span>";
    $("posCount").textContent = String((snap.positions || []).length);

    var positions = snap.positions || [];
    if (!positions.length) {
      $("book").innerHTML = '<div class="empty">No open paper positions.</div>';
    } else {
      $("book").innerHTML =
        "<table class='mono'><thead><tr><th>Sym</th><th>Qty</th><th>Last</th><th>P&L</th></tr></thead><tbody>" +
        positions.map(function (p) {
          return (
            "<tr><td>" + escapeHtml(p.symbol || "") + "</td><td>" +
            Number(p.qty || 0).toFixed(4) + "</td><td>" +
            money(Number(p.last || 0)) + "</td><td class='" + cls(Number(p.pnl || 0)) + "'>" +
            money(Number(p.pnl || 0)) + "</td></tr>"
          );
        }).join("") +
        "</tbody></table>";
    }

    var feed = (snap.feed || []).slice(0, 24);
    if (!feed.length) {
      $("feed").innerHTML = '<div class="empty">Feed quiet.</div>';
    } else {
      $("feed").innerHTML = feed.map(function (ev) {
        var ts = String(ev.ts || "").replace("T", " ").replace("Z", "");
        return (
          "<div class='event'><time class='mono'>" + escapeHtml(ts.slice(11, 19) || ts) +
          "</time><div>" + escapeHtml(ev.text || ev.kind || "") + "</div></div>"
        );
      }).join("");
    }

    var quotes = snap.quotes || [];
    $("tape").textContent = quotes.length
      ? quotes.map(function (q) {
          var ch = typeof q.change_pct === "number" ? pct(q.change_pct) : "";
          return (q.symbol || "") + " " + (q.last != null ? Number(q.last).toFixed(2) : "--") + " " + ch;
        }).join("   ·   ")
      : "tape empty";
  }

  function loadSnapshot() {
    return fetchJson(LOCAL_DATA).catch(function () {
      return fetchJson(REMOTE_DATA);
    });
  }

  function tick() {
    Promise.all([
      loadSnapshot().catch(function () { return null; }),
      probe(LIVE1),
      probe(LIVE1_JS),
    ]).then(function (parts) {
      var snap = parts[0];
      var host = parts[1];
      var script = parts[2];
      if (snap) {
        snap.pulse = {
          ok: true,
          label: "live1",
          host: host,
          script: script,
        };
        render(snap, !snap._book && host && host.ok);
      } else {
        render({ positions: [], feed: [], quotes: [], equity: null, cash: null, pnl: null, pnl_pct: null }, false);
        $("status").textContent = "live1 waiting · host " + (host && host.ok ? "up" : "down");
      }
    });
  }

  tick();
  setInterval(tick, 4000);
})();
