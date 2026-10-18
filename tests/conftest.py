from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from news.service.db import create_engine_for, migrate


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = create_engine_for(f"sqlite:///{tmp_path / 'news.db'}")
    migrate(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session
