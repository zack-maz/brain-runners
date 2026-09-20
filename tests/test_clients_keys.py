import pytest

from bakeoff.clients.keys import require_key

NAME = "BAKEOFF_TEST_KEY"


def test_the_environment_wins_over_the_file(tmp_path, monkeypatch):
    env_file = tmp_path / "keys"
    env_file.write_text(f"{NAME}=from-file\n")
    monkeypatch.setenv(NAME, "from-environment")
    assert require_key(NAME, env_file) == "from-environment"


def test_the_file_is_read_inside_the_program_without_touching_the_environment(tmp_path, monkeypatch):
    import os

    env_file = tmp_path / "keys"
    env_file.write_text(f"OTHER=x\n{NAME}= from-file \n")
    monkeypatch.delenv(NAME, raising=False)
    assert require_key(NAME, env_file) == "from-file"
    assert NAME not in os.environ


@pytest.mark.parametrize("content", ["", f"{NAME}=\n", f"{NAME}=   \n"])
def test_a_missing_or_empty_key_is_a_value_error_that_names_the_key_only(tmp_path, monkeypatch, content):
    env_file = tmp_path / "keys"
    env_file.write_text(content)
    monkeypatch.delenv(NAME, raising=False)
    with pytest.raises(ValueError, match=f"{NAME} is not set"):
        require_key(NAME, env_file)


def test_a_missing_file_is_the_same_error(tmp_path, monkeypatch):
    monkeypatch.delenv(NAME, raising=False)
    with pytest.raises(ValueError, match="is not set"):
        require_key(NAME, tmp_path / "absent")
