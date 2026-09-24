// The standalone benchmark page: reads the numbers bakeoff/bench.py embedded and hands them to the
// one renderer (bench_view.js), which the replay's Analysis tab mounts too.
(function () {
  "use strict";
  const data = JSON.parse(document.getElementById("replay-data").textContent);
  const why = window.BenchView.why(data);
  if (why) {
    document.getElementById("empty").hidden = false;
    document.getElementById("empty").textContent = why;
    return;
  }
  document.getElementById("app").hidden = false;
  document.getElementById("game").textContent = `game ${data.game || "unknown"} · ${data.runs.length} runs`;
  window.BenchView.mount(document.getElementById("bench"), data);
})();
