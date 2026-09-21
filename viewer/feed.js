// The one way frames reach the page. A replay file and a live run look the same to it:
//
//   handlers.onMeta({runs, players, seeds, scoreboard})   once, from the embedded replay
//   handlers.onEpisode(episode, track)                    an episode begins; `episode` has no frames yet
//   handlers.onFrame(player, seed, frame, summary)        one decision; `summary` is the episode's
//                                                         {complete, finished, death_cause, rows_survived}
//                                                         after it, or null when the episode already says
//   handlers.onEnd({status, runs, scoreboard})            live only: the run is over
//   handlers.onError(message)                             live only
//
// fromEmbedded(replay) reads the object bakeoff/replay.py built (docs/REPLAY_DATA.md). fromStream(url)
// listens to `bakeoff live`, whose events carry the same shapes. The page never reads the replay object
// itself. Pure apart from the EventSource, which tests replace.
(function (root) {
  "use strict";

  const header = (episode) => {
    const copy = { ...episode };
    delete copy.frames;
    return copy;
  };

  function fromEmbedded(replay, handlers) {
    handlers.onMeta({ runs: replay.runs || [], players: replay.players || [], seeds: replay.seeds || [],
                      scoreboard: replay.scoreboard || { columns: [], rows: [], same_seeds: true } });
    for (const episode of replay.episodes || []) {
      handlers.onEpisode(header(episode), (replay.tracks || {})[String(episode.seed)]);
      for (const frame of episode.frames) handlers.onFrame(episode.player, episode.seed, frame, null);
    }
  }

  // Events: `episode` {episode, track}, `frame` {player, seed, frame, summary}, `end` {status, runs,
  // scoreboard}, `error` {message}. The server replays its history to a page that connects late or
  // reconnects, so an episode or a row that was already delivered is dropped here.
  function fromStream(url, handlers, EventSourceClass) {
    const Source = EventSourceClass || root.EventSource;
    const source = new Source(url);
    const lastRow = {}; // "player seed" -> the last row delivered
    const data = (event) => JSON.parse(event.data);
    source.addEventListener("episode", (event) => {
      const { episode, track } = data(event);
      const key = episode.player + " " + episode.seed;
      if (key in lastRow) return;
      lastRow[key] = -1;
      handlers.onEpisode(header(episode), track);
    });
    source.addEventListener("frame", (event) => {
      const { player, seed, frame, summary } = data(event);
      const key = player + " " + seed;
      if (!(key in lastRow) || frame.row <= lastRow[key]) return;
      lastRow[key] = frame.row;
      handlers.onFrame(player, seed, frame, summary || null);
    });
    source.addEventListener("end", (event) => {
      source.close(); // or the browser would reconnect and the run would seem to start again
      handlers.onEnd(data(event));
    });
    // a named `error` event is ours and carries JSON; a bare one is the browser's (the connection dropped)
    source.addEventListener("error", (event) => {
      if (event && typeof event.data === "string") handlers.onError(data(event).message);
      else handlers.onError(null);
    });
    return source;
  }

  const api = { fromEmbedded, fromStream };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Feed = api;
})(typeof window !== "undefined" ? window : globalThis);
