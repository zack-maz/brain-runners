import pandas as pd

from bakeoff.fly.shuffle import shuffled_connectivity


def connectivity():
    rows = [(0, 1, 3, 1), (0, 2, 1, 1), (1, 2, 2, -1), (2, 0, 5, 1), (2, 1, 1, -1), (3, 0, 4, 1), (3, 3, 2, -1)]
    df = pd.DataFrame(rows, columns=["Presynaptic_Index", "Postsynaptic_Index", "Connectivity", "Excitatory"])
    df["Presynaptic_ID"], df["Postsynaptic_ID"] = df["Presynaptic_Index"] + 100, df["Postsynaptic_Index"] + 100
    df["Excitatory x Connectivity"] = df["Connectivity"] * df["Excitatory"]
    return df


def degrees(df, column):
    return df.groupby([column, "Excitatory"]).size().to_dict()


def test_every_neuron_keeps_its_degrees_by_sign_and_every_connection_its_weight():
    before = connectivity()
    after = shuffled_connectivity(before, seed=3)
    assert degrees(after, "Presynaptic_Index") == degrees(before, "Presynaptic_Index")
    assert degrees(after, "Postsynaptic_Index") == degrees(before, "Postsynaptic_Index")
    columns = ["Presynaptic_Index", "Presynaptic_ID", "Connectivity", "Excitatory", "Excitatory x Connectivity"]
    assert after[columns].equals(before[columns])
    assert (after["Postsynaptic_ID"] == after["Postsynaptic_Index"] + 100).all()  # the id moves with the index


def test_the_same_seed_gives_the_same_wiring_and_the_input_is_left_alone():
    before = connectivity()
    first, again = shuffled_connectivity(before, seed=3), shuffled_connectivity(before, seed=3)
    assert first.equals(again)
    assert before.equals(connectivity())
    seeds = {tuple(shuffled_connectivity(before, seed=s)["Postsynaptic_Index"]) for s in range(20)}
    assert len(seeds) > 1
