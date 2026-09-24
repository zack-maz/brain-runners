// The two tabs, as a rule rather than a router: plain buttons over one page, no navigation, no build
// step. The tab in focus is remembered while the page is open and nowhere else. Pure, tested.
(function (root) {
  "use strict";

  const NAMES = ["run", "analysis"];

  // The tab to show: the one asked for when it exists, otherwise the one already in focus, otherwise
  // the run. A page that opens on nothing always opens on the race.
  function select(current, wanted) {
    if (NAMES.includes(wanted)) return wanted;
    return NAMES.includes(current) ? current : NAMES[0];
  }

  // What each tab's button and panel should be, given the tab in focus: aria-selected on the button,
  // hidden on the panel. Returned rather than applied, so the rule can be tested without a DOM.
  function stateOf(focus) {
    const chosen = select(focus, focus);
    return NAMES.map((name) => ({ name, selected: name === chosen, hidden: name !== chosen }));
  }

  // Arrow keys move along the tab strip and wrap, as a tab list should.
  function step(focus, key) {
    const at = NAMES.indexOf(select(focus, focus));
    if (key === "ArrowRight") return NAMES[(at + 1) % NAMES.length];
    if (key === "ArrowLeft") return NAMES[(at - 1 + NAMES.length) % NAMES.length];
    return null;
  }

  const api = { NAMES, select, stateOf, step };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Tabs = api;
})(typeof window !== "undefined" ? window : globalThis);
