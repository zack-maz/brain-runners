// The Brain Battle screens of `bakeoff live`, as a rule rather than a router, like the tabs: one page, one
// screen shown at a time, no navigation, nothing kept in the URL. Pure, tested.
//
//   home ─Launch─▶ select ─Ready─▶ track ─RUN─▶ run ─(the run ends)─▶ results
//   Records opens from home and from results, and Back returns to where it was opened from.
(function (root) {
  "use strict";

  const NAMES = ["home", "select", "track", "run", "results", "records"];

  // The screen to show: the one asked for when it exists, otherwise the one already shown, otherwise home.
  function select(current, wanted) {
    if (NAMES.includes(wanted)) return wanted;
    return NAMES.includes(current) ? current : NAMES[0];
  }

  // Where Back (the ‹ link, or Escape) leads from a screen. `from` is the screen Records was opened from.
  function back(screen, from) {
    if (screen === "select") return "home";
    if (screen === "track") return "select";
    if (screen === "records") return from === "results" ? "results" : "home";
    if (screen === "run" || screen === "results") return "home";
    return "home";
  }

  // What each screen's section should be: hidden unless it is the one shown. Returned rather than applied,
  // so the rule can be tested without a DOM.
  function stateOf(screen) {
    const shown = select(screen, screen);
    return NAMES.map((name) => ({ name, hidden: name !== shown }));
  }

  const api = { NAMES, select, back, stateOf };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Screens = api;
})(typeof window !== "undefined" ? window : globalThis);
