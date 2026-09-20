from pathlib import Path

from bakeoff.fly.calibrate import CONFIG_COLUMNS, play, report, score, search
from bakeoff.fly.reading import Reading
from bakeoff.fly.surface import LEVELS_HZ, measure_surface
from bakeoff.game.track import generate_track
from bakeoff.players import fly, make_player
from bakeoff.senses import LOOMING_FALLOFF, LOOMING_GAIN_HZ

NAMES = ("DNa01_left", "DNa01_right", "DNb01_left", "DNb01_right", "DNp01_left", "DNp01_right")


class ReflexBrain:
    """A cartoon of the real one: steering fires opposite the louder eye, the Giant Fiber with the sum."""

    window_ms = 100.0

    def window(self, left_hz, right_hz, noise_seed=None):
        counts = dict.fromkeys(NAMES, 0)
        counts["DNa01_right"] = int(max(left_hz - right_hz, 0) // 25)
        counts["DNa01_left"] = int(max(right_hz - left_hz, 0) // 25)
        counts["DNp01_left"] = counts["DNp01_right"] = int((left_hz + right_hz) // 25)
        return Reading(rates_hz={}, spike_counts=counts, spike_times_ms={}, total_spikes=0, wall_ms=0.0)


def surface():
    return measure_surface(ReflexBrain(), levels_hz=LEVELS_HZ, trials=1)


def test_play_returns_the_finished_game_and_the_actions_taken():
    track = generate_track(1000, max_rows=40)
    game, actions = play(make_player("solver"), track)
    assert game.over and game.rows_survived == 40
    assert sum(2 if a == "jump" else 1 for a in actions) >= 40


def test_score_summarises_a_player_over_tracks():
    tracks = [generate_track(seed, max_rows=40) for seed in (1000, 1001, 1002)]
    assert score(make_player("always_jump"), tracks)["jump_share"] == 1.0
    solver = score(make_player("solver"), tracks)
    assert solver == {"mean_rows": 40.0, "median_rows": 40, "finished": 3, "jump_share": solver["jump_share"]}


def test_search_scores_every_candidate_and_puts_the_best_first():
    tracks = [generate_track(seed, max_rows=60) for seed in range(1000, 1006)]
    results = search(surface(), tracks, gains_hz=(100.0,), falloffs=(1.0, 2.0),
                     turn_thresholds_hz=(10.0, 1000.0), jump_thresholds_hz=(100.0, 1000.0))
    assert len(results) == 8
    assert [r["mean_rows"] for r in results] == sorted((r["mean_rows"] for r in results), reverse=True)
    never_moves = [r for r in results if r["turn_threshold_hz"] == 1000.0 and r["jump_threshold_hz"] == 1000.0]
    assert all(r["jump_share"] == 0.0 for r in never_moves)
    assert results[0]["mean_rows"] > never_moves[0]["mean_rows"]  # reacting beats running straight
    assert search(surface(), tracks, gains_hz=(100.0,), falloffs=(1.0, 2.0),
                  turn_thresholds_hz=(10.0, 1000.0), jump_thresholds_hz=(100.0, 1000.0)) == results


def test_report_names_the_winner_and_says_whose_tuning_it_is():
    tracks = [generate_track(seed, max_rows=40) for seed in (1000, 1001)]
    results = search(surface(), tracks, gains_hz=(100.0,), falloffs=(1.0,),
                     turn_thresholds_hz=(10.0,), jump_thresholds_hz=(100.0, 150.0))
    floors = [{"player": "random", **score(make_player("random"), tracks)}]
    solver = score(make_player("solver"), tracks)
    text = report(surface(), results, held_out=solver, check=solver, floors=floors)
    assert "OUR tuning, not the fly's biology" in text
    assert "| " + " | ".join(CONFIG_COLUMNS) in text and "## Winner" in text and "| random |" in text
    assert "2 candidates" in text and "121 inputs x 1 trials" in text
    assert "--players fly --seeds 20 --seed-start 1000" in text


def test_the_committed_constants_are_the_calibration_winner():
    text = (Path(__file__).resolve().parents[1] / "calibration" / "REPORT.md").read_text()
    winner_row = text.split("## Winner\n\n")[1].splitlines()[2]
    winner = tuple(float(cell) for cell in winner_row.strip("| ").split(" | ")[:4])
    assert winner == (LOOMING_GAIN_HZ, LOOMING_FALLOFF, fly.TURN_THRESHOLD_HZ, fly.JUMP_THRESHOLD_HZ)
    assert fly.CALIBRATED
