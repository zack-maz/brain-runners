# Setting up Brain Runners with your own keys

Everything here runs on your own machine. Nothing is hosted, nothing is sent anywhere except the requests your
paid minds make to their providers, with your keys.

## 1. Install

You need [uv](https://docs.astral.sh/uv/) (it installs Python 3.13 for you) and git. Node is optional: it only
runs the page's own tests.

    git clone https://github.com/zack-maz/brain-runners.git
    cd brain-runners
    uv sync
    uv run pytest                                    # the fast tests, about 20 s; they never touch the network

## 2. Open Brain Runners

    uv run brain-runners

It opens `http://127.0.0.1:8000/` in your browser (the server listens on this machine only). The first time, it
downloads the study's recorded runs (7 MB, free) from the repository's GitHub Release into `runs/` (git-ignored),
after checking the download against a recorded sha256; with them, Records, Charts, the Writeup and every recorded
run work at once, with no keys. If the download fails the page opens anyway, and
`uv run python -m scripts.study_data fetch` tries again.

From the home screen: **Launch** picks runners and a track and plays it, **Records** lists past runs to watch
again, **Charts** has the study's numbers, **Writeup** the write-up. Ctrl-C stops the server. Every flag of
`bakeoff live` works here too (`uv run brain-runners --help`), e.g. `--port 8001` if 8000 is taken.
`uv run python -m bakeoff live` is the same server without the download and without opening the browser.

The three bots (solver, random, always jump) play for free, and until you add keys (step 3) and a cap (step 4) or
the fly data (step 5) they are the runners the page picks for you. `docs/WALKTHROUGH.md` explains every screen.

## 3. Your keys

Copy the template and fill in the keys for the minds you want:

    cp .env.example .env

| key | for | where |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude Haiku (`haiku_*`) | the Anthropic Console; API use is billed separately from a Claude subscription |
| `TYPESAFE_API_KEY` | Jev (`jev_*`) | TypeSafe |
| `ZHIPU_API_KEY` | GLM Flash (`glm_*`) | Z.ai; the Flash model is on its free tier, which is slow (up to about 18 s a decision) |

`.env` is git-ignored. The program reads it itself and never prints a key. A mind whose key is missing is refused
before anything plays, with the key's name in the message.

## 4. How spending is kept in your hands

- **Nothing is spent unless you allow it.** Every paid mind has a hard cap on live requests, `--max-requests`,
  per mind. The default is 0: a mind may only replay answers already cached, and stops at its first new question.
- **Set the cap when you start the server,** for example `uv run brain-runners --max-requests 150` lets
  each paid mind make at most 150 requests in that session (one track is at most 150 rows, one request a row).
- **The page asks before it spends.** The track select shows each runner's worst case (rows × requests × price)
  and the RUN button becomes CONFIRM, "spend at most …"; only a second, separate press starts the run.
- **Every answer is cached** (`.cache/responses`), so playing the same track again with the same minds is free.
- **A mind that reaches its cap, or whose provider keeps failing, drops out** and the others play on.

What a request costs, measured (`bakeoff/prices.py`, `docs/COSTS.md`):

| mind | USD per request | a whole track (150 rows), at most |
|---|---|---|
| `haiku_plain` | 0.0006 | 0.09 |
| `haiku_step1` | 0.0010 | 0.15 |
| `haiku_guided` | 0.0009 | 0.14 |
| `haiku_step2` | 0.0016 | 0.24 |
| `haiku_map` | 0.0065 | 0.98 |
| `jev_*` | about 0.00003 to 0.00012 (an estimate from tokens; your TypeSafe plan decides) | under 0.02 |
| `glm_*` | 0 on the free tier | 0 |

Real runs cost less than the worst case: most minds die before row 150.

## 5. The flies (optional, 400 MB)

    uv run python -m scripts.fetch_fly_data          # the fly model and FlyWire's annotations into data/

The fly model is Shiu et al.'s [Drosophila_brain_model](https://github.com/philshiu/Drosophila_brain_model) and
the annotations are [FlyWire's](https://github.com/flyconnectome/flywire_annotations), both pinned to a commit and
checked by sha256; they come from their authors under their own terms. A fly brain needs about 1 GB of memory and
a minute to build, then plays about a row a second. Run one fly process at a time: `live` builds one brain shared
by both flies. `uv run pytest -m slow` tests the real brain.

## 6. From the command line

    uv run python -m bakeoff run --players solver,random --seeds 5 --seed-start 1000     # play tracks, record a run
    uv run python -m bakeoff bench runs/<run_id>                                          # score runs (free)
    uv run python -m bakeoff view runs/<run_id>                                           # one offline replay page

Tracks are numbered by seed. Seeds 1000 and up are practice tracks; 100 to 199 are the study's held-out tracks,
and a paid mind may only spend on a seed below 1000 with `--held-out`. `docs/WALKTHROUGH.md` covers every command.
