import json

from core.config import Config
from core.paths import Paths


def test_load_recovers_from_corrupted_file(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    config_file = tmp_path / "config.json"
    config_file.write_text("{not valid json", encoding="utf-8")

    config = Config()

    # Defaults greifen, App crasht nicht auf der kaputten Datei.
    assert config.data["auto_sync"] is True

    # Die kaputte Datei wurde gesichert statt stillschweigend verworfen.
    backup_file = tmp_path / "config.json.bak"
    assert backup_file.exists()
    assert backup_file.read_text(encoding="utf-8") == "{not valid json"

    # config.json selbst enthält danach wieder gültiges JSON mit Defaults.
    assert json.loads(config_file.read_text(encoding="utf-8"))["auto_sync"] is True


def test_save_leaves_no_temp_file_and_is_reloadable(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    config = Config()
    config.data["sync_interval"] = 42
    config.save()

    assert not (tmp_path / "config.json.tmp").exists()

    reloaded = Config()
    assert reloaded.data["sync_interval"] == 42


def test_load_backfills_missing_defaults_without_dropping_existing_values(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(Paths, "config", staticmethod(lambda: tmp_path))

    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({"classic_path": "/some/path"}),
        encoding="utf-8",
    )

    config = Config()

    assert config.data["classic_path"] == "/some/path"
    assert config.data["sync_interval"] == 5
