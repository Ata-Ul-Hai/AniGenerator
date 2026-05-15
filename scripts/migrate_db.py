"""Run Alembic migrations to the latest revision."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    alembic_ini = project_root / "backend" / "alembic.ini"

    if not alembic_ini.exists():
        logger.error("Alembic config not found at %s", alembic_ini)
        raise FileNotFoundError(f"Missing alembic.ini: {alembic_ini}")

    logger.info("Running Alembic migrations from %s", alembic_ini)
    config = Config(str(alembic_ini))

    import time
    max_retries = 5
    for attempt in range(max_retries):
        try:
            command.upgrade(config, "head")
            logger.info("Alembic migrations completed successfully")
            return
        except Exception as e:
            logger.warning(f"Alembic migration attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                logger.info("Retrying in 2 seconds...")
                time.sleep(2)
            else:
                logger.exception("Alembic migration failed after maximum retries")
                raise


if __name__ == "__main__":
    main()
