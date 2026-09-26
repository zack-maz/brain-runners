import json
import re

import pytest

from bakeoff.__main__ import main
from bakeoff.roster import roster_json
from bakeoff.view import DATA_SLOT, VIEWER_DIR, embed_json, render_html

DATA = re.compile(r'<script type="application/json" id="replay-data">(.*?)</script>', re.S)


def test_embedded_json_cannot_close_its_script_element():
    value = {"text": "</script><script>alert(1)</script><!--", "n": 1}
    embedded = embed_json(value)
    assert "<" not in embedded
    assert json.loads(embedded) == value


def test_render_inlines_every_file_and_the_data():
    replay = {"replay_version": 1, "episodes": [], "note": "</script>"}
    page = render_html(replay)
    assert "<link" not in page and "<script src" not in page  # one file: nothing left to fetch
    for name in ("timeline.js", "tunnel.js", "sprites.js", "stage.js", "minds.js", "feed.js", "app.js"):
        assert (VIEWER_DIR / name).read_text() in page
    rules = (VIEWER_DIR / "viewer.css").read_text().split("}\n\n", 1)[1]  # everything after the two font faces
    assert rules in page
    (data,) = DATA.findall(page)
    assert json.loads(data) == replay
    assert DATA_SLOT not in page


def test_every_page_carries_the_roster_live_or_replay():
    for page in (render_html({"episodes": []}), render_html({"episodes": []}, live="/events", token="t")):
        (data,) = re.findall(r'<script type="application/json" id="roster-data">(.*?)</script>', page, re.S)
        assert json.loads(data) == roster_json()


def test_the_page_makes_no_network_request():
    page = render_html({"episodes": []})
    assert not re.search(r"""(src|href)=["']?(https?:)?//""", page)
    assert "@import" not in page
    styles = "".join(re.findall(r"<style>(.*?)</style>", page, re.S))
    assert all(url.startswith("data:") for url in re.findall(r"url\(([^)]*)\)", styles, re.I))  # only embedded data
    assert not re.search(r"@import|image-set|https?:", styles, re.I)


def test_the_page_says_what_is_ours_about_jev_and_the_figures():
    page = " ".join(render_html({"episodes": []}).split())
    assert "The wording of those questions and that rule are ours, not TypeSafe's" in page
    assert "looks one step ahead only" in page
    assert "landed on a gap about as often as always staying would have" in page
    assert "our own drawing and nobody's official artwork" in page
    assert ("The blue marks the mind in focus and the tiles it was shown; elsewhere it is a skin's own colour, "
            "where the user chose blue.") in page
    assert ("a skin that gives no such number shows no gauge (its slit is the visor's own colour, "
            "or the Map skin's blue)") in page


def test_the_page_keeps_every_caveat_about_the_fly_and_about_jevs_questions():
    page = " ".join(render_html({"episodes": []}).split())
    for caveat in ("The fly does not plan.", "a whole eye is stimulated at one rate", "leans right (0 to +20 Hz",
                   "a mild left bias in DNa02", "no spontaneous activity and no memory between decisions",
                   "comes from published steering studies, not from anything verified in this project",
                   "Giant Fiber rates of 100 to 200 Hz are not realistic",
                   "TypeSafe runs the questions of one request in parallel and they cannot see one another's answers"):
        assert caveat in page, caveat


def test_the_page_carries_the_chart_rules_the_analysis_tab_draws_with():
    """Without bench.css the Analysis tab's charts are black on black: nothing in the tests sees colour."""
    page = render_html({"episodes": []})
    assert ".chart .line" in page and '[data-bench="players"] th' in page


def test_every_script_the_page_names_exists_and_app_comes_last():
    names = re.findall(r'<script src="([^"]+)"></script>', (VIEWER_DIR / "index.html").read_text())
    assert names == ["timeline.js", "tunnel.js", "sprites.js", "roster.js", "stage.js", "minds.js", "log.js", "picker.js", "tabs.js",
                     "feed.js", "lobby.js", "bench.js", "bench_view.js", "screens.js", "select.js", "trackpick.js", "front.js", "app.js"]
    assert all((VIEWER_DIR / name).is_file() for name in names)


def test_the_two_brand_fonts_are_embedded_not_fetched():
    page = render_html({"episodes": []})
    fonts = re.findall(r"@font-face\s*{[^}]*}", page)
    assert len(fonts) == 2
    assert {re.search(r'font-family:\s*"([^"]+)"', f).group(1) for f in fonts} == {"Hanken Grotesk", "JetBrains Mono"}
    for face in fonts:
        (source,) = re.findall(r"url\(([^)]*)\)", face)
        assert source.startswith("data:font/woff2;base64,") and len(source) > 40_000
    assert "url(fonts/" not in page and ".woff2" not in page


def test_a_stylesheet_url_that_is_not_a_bundled_font_is_an_error(tmp_path):
    (tmp_path / "index.html").write_text('<link rel="stylesheet" href="a.css">' + DATA_SLOT)
    (tmp_path / "a.css").write_text("body { background: url(https://example.com/x.png); }")
    with pytest.raises(ValueError, match="a.css may only load fonts/<name>.woff2"):
        render_html({}, tmp_path)
    # url() is case-insensitive in CSS, and it is not the only way a stylesheet can fetch something
    for css in ("body { background: URL(https://example.com/x.png); }", "body { background: Url( 'fonts/../x.woff2' ); }",
                '@import "https://example.com/a.css";', "@IMPORT 'b.css';",
                'body { background: image-set("https://example.com/x.png" 1x); }',
                "/* see http://example.com */ body { color: red; }"):
        (tmp_path / "a.css").write_text(css)
        with pytest.raises(ValueError, match="a.css may only load fonts/<name>.woff2"):
            render_html({}, tmp_path)
    (tmp_path / "a.css").write_text('@font-face { font-family: "X"; src: url(fonts/missing.woff2) format("woff2"); }')
    with pytest.raises(FileNotFoundError):
        render_html({}, tmp_path)


def test_a_backslash_in_a_viewer_file_survives(tmp_path):
    (tmp_path / "index.html").write_text('<link rel="stylesheet" href="a.css"><script src="a.js"></script>' + DATA_SLOT)
    (tmp_path / "a.css").write_text('i::before { content: "\\1F41D"; }')
    (tmp_path / "a.js").write_text('const s = "\\n\\1";')
    page = render_html({}, tmp_path)
    assert 'content: "\\1F41D"' in page and 'const s = "\\n\\1";' in page


def test_a_page_without_the_data_slot_is_an_error(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>")
    with pytest.raises(ValueError, match="replay data slot"):
        render_html({}, tmp_path)


def test_view_writes_one_html_file_with_the_runs_in_it(tmp_path, capsys):
    assert main(["run", "--players", "solver,random", "--seeds", "2", "--max-rows", "30", "--out", str(tmp_path)]) == 0
    (run_dir,) = tmp_path.iterdir()
    output = tmp_path / "out.html"
    capsys.readouterr()
    assert main(["view", str(run_dir), "--output", str(output)]) == 0
    assert f"replay: {output} (4 episodes" in capsys.readouterr().out
    (data,) = DATA.findall(output.read_text())
    replay = json.loads(data)
    assert replay["players"] == ["solver", "random"] and replay["seeds"] == [0, 1]
    assert replay["runs"][0]["run_id"] == run_dir.name


def test_view_usage_errors(tmp_path, capsys):
    assert main(["view", str(tmp_path / "nope"), "--output", str(tmp_path / "out.html")]) == 2
    assert "no such run directory" in capsys.readouterr().err
    (tmp_path / "empty").mkdir()
    assert main(["view", str(tmp_path / "empty"), "--output", str(tmp_path / "out.html")]) == 2
    assert "no step records" in capsys.readouterr().err
    assert main(["run", "--players", "solver", "--seeds", "1", "--max-rows", "20", "--out", str(tmp_path / "runs")]) == 0
    (run_dir,) = (tmp_path / "runs").iterdir()
    assert main(["view", str(run_dir), str(run_dir), "--output", str(tmp_path / "out.html")]) == 2
    assert "solver on seed 0 is in both" in capsys.readouterr().err
    assert not (tmp_path / "out.html").exists()
    assert main(["view", str(run_dir), "--output", str(tmp_path / "nodir" / "out.html")]) == 2
    assert "cannot write" in capsys.readouterr().err


def test_the_benchmark_page_is_filled_the_same_way():
    page = render_html({"players": [{"player": "</script>"}]}, page_name="bench.html")
    assert '"player":"\\u003c/script>"' in page and "<script src=" not in page and '<link rel="stylesheet"' not in page


def test_the_benchmark_page_makes_no_network_request_and_names_only_existing_scripts():
    page = render_html({}, page_name="bench.html")
    assert not re.search(r"(src|href)=[\"']?https?:", page) and "@import" not in page
    source = (VIEWER_DIR / "bench.html").read_text()
    scripts = re.findall(r'<script src="([^"]+)"></script>', source)
    assert scripts == ["bench.js", "bench_view.js", "bench_app.js"] and all((VIEWER_DIR / s).exists() for s in scripts)


BENCH = re.compile(r'<script type="application/json" id="bench-data">(.*?)</script>', re.S)


def test_the_benchmark_rides_in_its_own_slot_and_leaves_the_replay_alone():
    page = render_html({"episodes": []}, bench={"players": [{"player": "solver"}]})
    assert json.loads(BENCH.search(page).group(1)) == {"players": [{"player": "solver"}]}
    assert json.loads(DATA.search(page).group(1)) == {"episodes": []}


def test_a_page_given_no_benchmark_keeps_an_empty_slot():
    page = render_html({"episodes": []})
    assert json.loads(BENCH.search(page).group(1)) is None


def test_a_benchmark_cannot_close_its_script_element_either():
    page = render_html({"episodes": []}, bench={"notes": ["</script><script>alert(1)</script>"]})
    assert "</script><script>alert(1)" not in page
    assert json.loads(BENCH.search(page).group(1))["notes"] == ["</script><script>alert(1)</script>"]


def test_the_benchmark_page_has_no_slot_for_a_benchmark_and_refuses_one():
    """bench.html carries its numbers in the replay slot; giving it a second set would lose them."""
    with pytest.raises(ValueError, match="benchmark data slot"):
        render_html({}, page_name="bench.html", bench={"players": []})


def test_view_writes_the_benchmark_of_the_runs_it_merges(tmp_path, capsys):
    from tests.test_replay import DIED, record, write_run

    records = ([record(player="solver", seed=1000, row=r) for r in range(9)] + [record(player="solver", seed=1000, row=9, **DIED)])
    run = write_run(tmp_path, "r", records, {"game": None})
    out = tmp_path / "page.html"
    assert main(["view", str(run), "--out", str(out)]) == 0
    numbers = json.loads(BENCH.search(out.read_text()).group(1))
    assert [p["player"] for p in numbers["players"]] == ["solver"]


def test_view_still_builds_a_page_when_there_is_nothing_to_score(tmp_path):
    """A run that never ended has no benchmark; the page says why rather than failing to build."""
    from tests.test_replay import record, write_run

    run = write_run(tmp_path, "open", [record(player="solver", seed=1000, row=0)], {"game": None})
    out = tmp_path / "page.html"
    assert main(["view", str(run), "--out", str(out)]) == 0
    assert "why" in json.loads(BENCH.search(out.read_text()).group(1))
