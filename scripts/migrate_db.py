"""Run Alembic migrations to the latest revision."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    alembic_ini = project_root / "backend" / "alembic.ini"

    config = Config(str(alembic_ini))
    command.upgrade(config, "head")


if __name__ == "__main__":
    main()
