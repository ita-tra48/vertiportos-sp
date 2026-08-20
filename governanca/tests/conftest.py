import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import banco


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    (tmp_path / "governanca" / "schemas").mkdir(parents=True)
    origem = Path(__file__).resolve().parents[1] / "schemas" / "schema.sql"
    (tmp_path / "governanca" / "schemas" / "schema.sql").write_text(
        origem.read_text())
    monkeypatch.setattr(banco, "RAIZ", tmp_path)
    monkeypatch.setattr(banco, "DB", tmp_path / "governanca" / "projeto.duckdb")
    monkeypatch.setattr(banco, "DUMP", tmp_path / "governanca" / "dump.sql")
    monkeypatch.setattr(banco, "SCHEMA",
                        tmp_path / "governanca" / "schemas" / "schema.sql")
    monkeypatch.setattr(banco, "_CON", None)
    yield tmp_path
    banco._CON = None
