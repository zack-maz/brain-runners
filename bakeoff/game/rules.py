"""Named game versions: everything that defines a game, in one frozen record. Pure.

A run records its rules in meta.json; runs of different games never share a scoreboard. v1 is the game
phases 1 to 5 were played on; v2 is shorter and gets hard sooner, so the players separate earlier
(docs/superpowers/specs/2026-09-21-game-v2-design.md)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class Rules:
    version: str
    lanes: int
    max_rows: int
    lookahead: int  # rows a player is shown
    window: int  # lanes a player is shown either side of its own
    runway_rows: int  # rows 0..runway_rows are all floor so nobody dies before seeing a gap
    start_gap_rate: float  # chance that a lane starts a gap run, at row 0
    end_gap_rate: float  # the same chance from row difficulty_rows on
    difficulty_rows: int  # gap density ramps over this many rows whatever max_rows is, so tracks are prefix-stable
    max_gap_width: int

    def __post_init__(self):
        # every action's landing tile must be in sight: a jump lands two rows on, a dodge one lane over
        if self.lookahead < 2:
            raise ValueError(f"lookahead must be at least 2 (a jump lands two rows on), not {self.lookahead}")
        if not 1 <= self.window <= (self.lanes - 1) // 2:
            raise ValueError(f"window must be 1 to {(self.lanes - 1) // 2} lanes, not {self.window}")

    def variant(self, max_rows: int | None = None, lookahead: int | None = None, window: int | None = None) -> Rules:
        """A copy for tests and experiments. A different vision is a different game and says so in its
        version (`v2+look3`, `v2+look8+win4`); a different length plays a prefix of the same tracks, so
        it keeps the version and is recorded in `max_rows`. The name is built from the base version (not
        from whatever this instance happens to already be called), so chaining variants back to the
        base's own lookahead/window collapses back to the base's plain name."""
        base_name = self.version.split("+")[0]
        base = RULES.get(base_name, self)
        new_lookahead = self.lookahead if lookahead is None else lookahead
        new_window = self.window if window is None else window
        version = base_name
        if new_lookahead != base.lookahead:
            version += f"+look{new_lookahead}"
        if new_window != base.window:
            version += f"+win{new_window}"
        return replace(self, version=version, max_rows=self.max_rows if max_rows is None else max_rows,
                       lookahead=new_lookahead, window=new_window)

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, block: dict) -> Rules:
        """The rules of a recorded run. A `game` block without `version` was written before versions
        existed, on v1. A field a future version of this dataclass has but an older recorded block does
        not is filled from the named base version, so a field added later does not make every run
        recorded today unreadable; if the base version is unknown, or a field is still missing, reading
        fails loudly instead of guessing."""
        if "version" not in block:
            return V1.variant(max_rows=block.get("max_rows"), lookahead=block.get("lookahead"),
                              window=block.get("window"))
        version = block["version"]
        base = RULES.get(version.split("+")[0])
        fields = {}
        for k in cls.__dataclass_fields__:
            if k in block:
                fields[k] = block[k]
            elif base is not None and hasattr(base, k):
                fields[k] = getattr(base, k)
            else:
                raise ValueError(f"cannot read game {version!r}: missing {k!r} and no known base version to fill it from")
        return cls(**fields)

    def same_game(self, other: Rules) -> bool:
        """Equal in everything but length: a shorter run plays a prefix of the same tracks."""
        return replace(self, max_rows=0) == replace(other, max_rows=0)


V1 = Rules(version="v1", lanes=12, max_rows=300, lookahead=6, window=3, runway_rows=4, start_gap_rate=0.04,
           end_gap_rate=0.16, difficulty_rows=300, max_gap_width=3)
V2 = replace(V1, version="v2", max_rows=150, difficulty_rows=100)
RULES = {"v1": V1, "v2": V2}
DEFAULT = "v2"


def rules_for(version: str) -> Rules:
    if version not in RULES:
        raise ValueError(f"unknown game version {version!r}; known: {', '.join(RULES)}")
    return RULES[version]


def resolve(rules: Rules | None = None, max_rows: int | None = None) -> Rules:
    """`rules` (default: the current version), `max_rows` rows long if given."""
    return (rules or RULES[DEFAULT]).variant(max_rows=max_rows)
