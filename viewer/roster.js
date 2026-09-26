// The roster as the page reads it (bakeoff/roster.py, embedded by bakeoff/view.py): each player's
// character and skin, the label the select screen gives it ("Jev · Step 1"), how its sprite is coloured,
// and the ink its label can be written in. Pure and tested under node.
(function (root) {
  "use strict";

  const GROUND = "#0A0A0A"; // the page's background (--bg): a label must be readable on it
  const MIN_CONTRAST = 3; // WCAG's floor for large or bold text; the labels are short and bold

  // relative luminance of a #RRGGBB colour (WCAG 2)
  function luminance(hex) {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
      .map((c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)));
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  function contrast(a, b) {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  }

  // `data` is the embedded roster, or null (a page built before the roster): then every player keeps its
  // upper-case name and the grey block, as before.
  function make(data) {
    const bySkin = new Map();
    for (const character of data || []) {
      for (const skin of character.skins || []) bySkin.set(skin.player, { character, skin });
    }
    const found = (player) => bySkin.get(player) || null;
    return {
      has: (player) => bySkin.has(player),
      label: (player) => {
        const f = found(player);
        return f ? f.character.name + " · " + f.skin.name : String(player).toUpperCase();
      },
      // what Sprites.drawSprite needs: the character's sprite and the skin's colours
      look: (player) => {
        const f = found(player);
        return f ? { sprite: f.character.sprite, color: f.skin.color, inks: f.skin.inks || {} }
          : { sprite: "block", color: null, inks: {} };
      },
      // the skin's colour for its label, or null where it would not read on the page's dark ground (the Map
      // skins' black): the label then keeps the page's own ink, and the swatch beside it shows the colour
      ink: (player) => {
        const f = found(player);
        return f && contrast(f.skin.color, GROUND) >= MIN_CONTRAST ? f.skin.color : null;
      },
      colour: (player) => (found(player) ? found(player).skin.color : null),
    };
  }

  const api = { make, luminance, contrast };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Roster = api;
})(typeof window !== "undefined" ? window : globalThis);
