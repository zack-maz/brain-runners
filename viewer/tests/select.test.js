const test = require("node:test");
const assert = require("node:assert/strict");
const Select = require("../select.js");

// a slice of bakeoff/roster.py's JSON: a character with two skins, one with three, one with one
const skin = (player, name, color) => ({ player, name, about: name + " does <this>.", color, inks: {} });
const ROSTER = [
  { id: "fly", name: "Fly", sprite: "fly", skins: [skin("fly", "Looming", "#AEB4BA"), skin("fly2", "Sideways", "#F7768E")] },
  { id: "jev", name: "Jev", sprite: "visor", skins: [skin("jev_plain", "Plain", "#B9BEC4"), skin("jev_guided", "Guided", "#5FA35A"),
                                                      skin("jev_step1", "Step 1", "#E6B422")] },
  { id: "bot", name: "Bot", sprite: "bot", skins: [skin("random", "Random", "#8A9097")] },
];
const empty = () => Select.make(ROSTER, []);

test("a click drops the next token, in the character's first skin not already in a slot", () => {
  let sel = Select.add(empty(), ROSTER, 1);
  sel = Select.add(sel, ROSTER, 1);
  assert.deepEqual(Select.players(sel, ROSTER), ["jev_plain", "jev_guided"]);
  assert.equal(sel.focus, 1); // the new slot takes the focus
  assert.equal(sel.cursor, 1);
});

test("a character whose skins are all in takes no more tokens, and neither does a ninth slot", () => {
  let sel = Select.add(Select.add(empty(), ROSTER, 0), ROSTER, 0);
  assert.deepEqual(Select.add(sel, ROSTER, 0), sel);
  sel = empty();
  for (let i = 0; i < 12; i++) sel = Select.add(sel, ROSTER, i % 3);
  assert.equal(sel.slots.length, 6); // 2 + 3 + 1 skins: every one in, none twice
  assert.equal(new Set(Select.players(sel, ROSTER)).size, 6);
});

test("the eight-slot limit", () => {
  const big = [{ id: "many", name: "Many", sprite: "bot", skins: Array.from({ length: 10 }, (_, k) => skin("p" + k, "S" + k, "#8A9097")) }];
  let sel = Select.make(big, []);
  for (let i = 0; i < 10; i++) sel = Select.add(sel, big, 0);
  assert.equal(sel.slots.length, Select.MAX);
  assert.equal(Select.MAX, 8);
});

test("X and Y cycle the focused slot's skin, skipping skins another slot has", () => {
  let sel = Select.add(Select.add(empty(), ROSTER, 1), ROSTER, 1); // jev_plain, jev_guided (focused)
  sel = Select.cycle(sel, ROSTER, 1);
  assert.deepEqual(Select.players(sel, ROSTER), ["jev_plain", "jev_step1"]);
  sel = Select.cycle(sel, ROSTER, 1); // plain is taken by P1: it wraps past it to guided
  assert.deepEqual(Select.players(sel, ROSTER), ["jev_plain", "jev_guided"]);
  sel = Select.cycle(sel, ROSTER, -1); // backwards: plain is taken, so step 1
  assert.deepEqual(Select.players(sel, ROSTER), ["jev_plain", "jev_step1"]);
});

test("a dot sets a skin, never one another slot has", () => {
  const sel = Select.add(Select.add(empty(), ROSTER, 0), ROSTER, 0); // fly, fly2
  assert.deepEqual(Select.setSkin(sel, 1, 0), sel); // fly is P1's
  const one = Select.add(empty(), ROSTER, 0);
  assert.deepEqual(Select.players(Select.setSkin(one, 0, 1), ROSTER), ["fly2"]);
});

test("removing a slot keeps the focus on a slot that exists", () => {
  let sel = Select.add(Select.add(Select.add(empty(), ROSTER, 0), ROSTER, 1), ROSTER, 2); // focus on P3
  sel = Select.remove(sel, 2);
  assert.deepEqual(Select.players(sel, ROSTER), ["fly", "jev_plain"]);
  assert.equal(sel.focus, 1);
  assert.equal(Select.remove(Select.remove(sel, 0), 0).slots.length, 0);
  assert.deepEqual(Select.remove(sel, 7), sel);
});

test("ready from one fighter on", () => {
  assert.equal(Select.ready(empty()), false);
  assert.equal(Select.ready(Select.add(empty(), ROSTER, 2)), true);
});

test("the keys: arrows move the cursor, Space adds, Backspace removes, Enter goes on only when ready", () => {
  let out = Select.onKey(empty(), ROSTER, "ArrowLeft");
  assert.equal(out.sel.cursor, 2); // it wraps
  out = Select.onKey(out.sel, ROSTER, " ");
  assert.deepEqual(Select.players(out.sel, ROSTER), ["random"]);
  assert.equal(Select.onKey(out.sel, ROSTER, "Enter").go, "track");
  assert.equal(Select.onKey(empty(), ROSTER, "Enter").go, null);
  assert.equal(Select.onKey(out.sel, ROSTER, "Escape").go, "back");
  assert.equal(Select.onKey(out.sel, ROSTER, "Backspace").sel.slots.length, 0);
  assert.equal(Select.onKey(out.sel, ROSTER, "q"), null);
});

test("the command line's players open the select, as far as the roster has them", () => {
  const sel = Select.make(ROSTER, ["jev_step1", "nobody", "fly", "jev_step1"]);
  assert.deepEqual(Select.players(sel, ROSTER), ["jev_step1", "fly"]);
  assert.equal(sel.cursor, 1);
});

test("a skin's price, as the select screen says it", () => {
  assert.equal(Select.priceText(ROSTER[1], { paid: true, price_usd: 0.00004 }), "paid · 0.00004 USD / request");
  assert.equal(Select.priceText(ROSTER[1], { paid: true, price_usd: 0 }), "free tier");
  assert.equal(Select.priceText(ROSTER[0], { paid: false }), "free · simulated");
  assert.equal(Select.priceText(ROSTER[2], { paid: false }), "free");
});

test("the markup: portraits with tokens, slots with dots, taken dots disabled, every text escaped", () => {
  const sel = Select.add(Select.add(empty(), ROSTER, 0), ROSTER, 0);
  const portraits = Select.portraitsHtml(sel, ROSTER);
  assert.match(portraits, /data-char="0" aria-current="true" aria-disabled="true"/); // both fly skins are in
  assert.equal((portraits.match(/class="token( focus)?"/g) || []).length, 2);
  assert.match(portraits, /data-player="fly" data-px="13"/); // the portrait is the default skin
  const slots = Select.slotsHtml(sel, ROSTER);
  assert.equal((slots.match(/class="slot empty"/g) || []).length, 6);
  assert.match(slots, /data-slot="1" data-skin="0" style="background:#AEB4BA" disabled aria-label="Looming \(already in\)"/);
  const info = Select.infoHtml(sel, ROSTER, [{ name: "fly2", paid: false, why_not: "not <now>" }]);
  assert.match(info, /Fly · Sideways · fly2/);
  assert.match(info, /Sideways does &#60;this&#62;\./);
  assert.match(info, /not &#60;now&#62;/);
  assert.match(Select.infoHtml(empty(), ROSTER, []), /Click a fighter/);
});
