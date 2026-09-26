// The character select, Smash-style: five portraits, eight slots, a skin per slot. The rules are here and
// tested; the markup is returned as strings and app.js puts it in the page. Sprites are left as empty
// canvases (`canvas.sprite[data-player]`) that app.js paints (Sprites.paint), so this file needs no DOM.
//
// `roster` is bakeoff/roster.py's JSON: [{id, name, sprite, skins: [{player, name, about, color, inks}]}].
// A selection is {slots: [{c, s}], focus, cursor}: `c` a character's index, `s` its skin's index, `focus`
// the slot the skin keys act on, `cursor` the portrait the arrow keys are on. Selections are never changed
// in place: every function returns a new one.
(function (root) {
  "use strict";

  const Minds_ = typeof require !== "undefined" ? require("./minds.js") : root.Minds;
  const Lobby_ = typeof require !== "undefined" ? require("./lobby.js") : root.Lobby;
  const esc = Minds_.esc;

  const MAX = 8; // the slots, P1 to P8

  const key = (c, s) => c + ":" + s;

  // The skins already in a slot, except slot `except` (the one being changed).
  function used(sel, except) {
    return new Set(sel.slots.filter((_, i) => i !== except).map((slot) => key(slot.c, slot.s)));
  }

  // The selection the page opens with: the players the command line offered (`--players`), in order, as far
  // as the roster has them; an old or unknown name, a duplicate, or a ninth is left out.
  function make(roster, players) {
    const slots = [];
    for (const player of players || []) {
      if (slots.length >= MAX) break;
      roster.forEach((character, c) => character.skins.forEach((skin, s) => {
        if (skin.player === player && !slots.some((slot) => slot.c === c && slot.s === s)) slots.push({ c, s });
      }));
    }
    return { slots: slots.slice(0, MAX), focus: 0, cursor: slots.length ? slots[0].c : 0 };
  }

  // A click on a portrait, or Space on the cursor's: the next free slot, in that character's first skin not
  // already taken. Nothing happens when the slots are full or every skin is in.
  function add(sel, roster, c) {
    if (sel.slots.length >= MAX || !roster[c]) return sel;
    const taken = used(sel, -1);
    const s = roster[c].skins.findIndex((_, k) => !taken.has(key(c, k)));
    if (s < 0) return sel;
    return { slots: sel.slots.concat([{ c, s }]), focus: sel.slots.length, cursor: c };
  }

  // A slot's dot: that skin, unless another slot already has it (one player cannot run twice on a track).
  function setSkin(sel, i, k) {
    const slot = sel.slots[i];
    if (!slot || used(sel, i).has(key(slot.c, k))) return sel;
    return { ...sel, slots: sel.slots.map((x, j) => (j === i ? { c: x.c, s: k } : x)), focus: i };
  }

  // X (dir 1) or Y (dir -1): the focused slot's next skin that no other slot has, wrapping around.
  function cycle(sel, roster, dir) {
    const slot = sel.slots[sel.focus];
    if (!slot) return sel;
    const n = roster[slot.c].skins.length;
    const taken = used(sel, sel.focus);
    for (let step = 1; step < n; step++) {
      const k = (((slot.s + dir * step) % n) + n) % n;
      if (!taken.has(key(slot.c, k))) return setSkin(sel, sel.focus, k);
    }
    return sel;
  }

  // A slot's ✕, or Backspace on the focused slot. The focus stays on a slot that still exists.
  function remove(sel, i) {
    if (!sel.slots[i]) return sel;
    const slots = sel.slots.filter((_, j) => j !== i);
    return { ...sel, slots, focus: Math.max(0, Math.min(sel.focus, slots.length - 1)) };
  }

  function focusSlot(sel, i) {
    return sel.slots[i] ? { ...sel, focus: i } : sel;
  }

  function moveCursor(sel, roster, dir) {
    return { ...sel, cursor: (((sel.cursor + dir) % roster.length) + roster.length) % roster.length };
  }

  // The players chosen, in slot order: what the track select and POST /run are given.
  function players(sel, roster) {
    return sel.slots.map((slot) => roster[slot.c].skins[slot.s].player);
  }

  const ready = (sel) => sel.slots.length >= 1;

  // A key on the select screen: the new selection, and where to go (`track` when ready and Enter is
  // pressed, `back` on Escape), or null for a key this screen does not use.
  function onKey(sel, roster, name) {
    if (name === "ArrowRight") return { sel: moveCursor(sel, roster, 1), go: null };
    if (name === "ArrowLeft") return { sel: moveCursor(sel, roster, -1), go: null };
    if (name === " ") return { sel: add(sel, roster, sel.cursor), go: null };
    if (name === "x" || name === "X") return { sel: cycle(sel, roster, 1), go: null };
    if (name === "y" || name === "Y") return { sel: cycle(sel, roster, -1), go: null };
    if (name === "Backspace") return { sel: remove(sel, sel.focus), go: null };
    if (name === "Enter") return { sel, go: ready(sel) ? "track" : null };
    if (name === "Escape") return { sel, go: "back" };
    return null;
  }

  // What a skin costs, as the select screen says it. `entry` is the player's line in GET /state.
  function priceText(character, entry) {
    if (entry && entry.paid) {
      return entry.price_usd > 0 ? "paid · " + Lobby_.usd(entry.price_usd) + " / request" : "free tier";
    }
    return character.id === "fly" ? "free · simulated" : "free";
  }

  // ---- the markup --------------------------------------------------------------------------------
  const sprite = (player, px) => '<canvas class="sprite" data-player="' + esc(player) + '" data-px="' + px + '"></canvas>';

  // The five portraits, each in its default skin, with the tokens of the slots that chose it.
  function portraitsHtml(sel, roster) {
    const taken = used(sel, -1);
    return roster.map((character, c) => {
      const free = character.skins.filter((_, k) => !taken.has(key(c, k))).length;
      const full = free === 0 || sel.slots.length >= MAX;
      const tokens = sel.slots.map((slot, i) => ({ slot, i })).filter((x) => x.slot.c === c)
        .map((x) => '<span class="token' + (x.i === sel.focus ? " focus" : "") + '">P' + (x.i + 1) + "</span>").join("");
      const count = character.skins.length + (character.skins.length === 1 ? " skin" : " skins");
      return '<button type="button" class="portrait" data-char="' + c + '"' +
        (c === sel.cursor ? ' aria-current="true"' : "") + (full ? ' aria-disabled="true"' : "") +
        ' aria-label="Add ' + esc(character.name) + '">' +
        '<span class="label count">' + esc(count) + '</span><span class="tokens">' + tokens + "</span>" +
        '<span class="art">' + sprite(character.skins[0].player, 13) + "</span>" +
        '<span class="name">' + esc(character.name) + "</span></button>";
    }).join("");
  }

  // The eight slots: a filled one shows its fighter in its skin and a dot per skin; an empty one says so.
  function slotsHtml(sel, roster) {
    let html = "";
    for (let i = 0; i < MAX; i++) {
      const slot = sel.slots[i];
      if (!slot) {
        html += '<div class="slot empty"><span class="label">P' + (i + 1) + "</span><span>Empty</span></div>";
        continue;
      }
      const character = roster[slot.c];
      const skin = character.skins[slot.s];
      const taken = used(sel, i);
      const dots = character.skins.map((other, k) => {
        const off = taken.has(key(slot.c, k));
        return '<button type="button" class="dot' + (k === slot.s ? " on" : "") + '" data-slot="' + i + '" data-skin="' + k + '"' +
          ' style="background:' + esc(other.color) + '"' + (off ? " disabled" : "") +
          ' aria-label="' + esc(other.name) + (off ? " (already in)" : "") + '"></button>';
      }).join("");
      html += '<div class="slot' + (i === sel.focus ? " focus" : "") + '" data-slot="' + i + '">' +
        '<div class="slot-top"><button type="button" class="label slot-label" data-focus="' + i + '">P' + (i + 1) + "</button>" +
        '<button type="button" class="remove" data-remove="' + i + '" aria-label="Remove P' + (i + 1) + '">✕</button></div>' +
        '<button type="button" class="slot-art" data-focus="' + i + '" aria-label="Select P' + (i + 1) + '">' +
        sprite(skin.player, 6) + "</button>" +
        '<span class="name">' + esc(character.name) + '</span><span class="skin">' + esc(skin.name) + "</span>" +
        '<span class="dots">' + dots + "</span></div>";
    }
    return html;
  }

  // The line about the focused slot: who it is, what it does, what it costs, and why it may not play.
  // `entries` is GET /state's players.
  function infoHtml(sel, roster, entries) {
    const slot = sel.slots[sel.focus];
    if (!slot) {
      return '<span class="hint">Click a runner to put it in the next free slot. Up to eight; one character can come in several skins.</span>';
    }
    const character = roster[slot.c];
    const skin = character.skins[slot.s];
    const entry = (entries || []).find((p) => p.name === skin.player);
    const price = priceText(character, entry);
    return '<span class="label who">P' + (sel.focus + 1) + "</span>" +
      '<span class="swatch" style="background:' + esc(skin.color) + '"></span>' +
      '<span class="title">' + esc(character.name + " · " + skin.name + " · " + skin.player) + "</span>" +
      '<span class="about">' + esc(skin.about) + "</span>" +
      (entry && entry.why_not ? '<span class="why warn">' + esc(entry.why_not) + "</span>" : "") +
      '<span class="label price' + (entry && entry.paid && entry.price_usd > 0 ? " paid" : "") + '">' + esc(price) + "</span>";
  }

  const api = { MAX, make, used, add, setSkin, cycle, remove, focusSlot, moveCursor, players, ready, onKey, priceText,
                portraitsHtml, slotsHtml, infoHtml };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Select = api;
})(typeof window !== "undefined" ? window : globalThis);
