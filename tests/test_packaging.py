"""AC-6: the wheel carries the migrations, so `news db upgrade` works without a source checkout."""

import subprocess
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_wheel_contains_the_migrations(tmp_path: Path) -> None:
    # The one slow test: it runs a real build.
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    [wheel] = tmp_path.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()

    assert "news/migrations/env.py" in names
    assert any(
        name.startswith("news/migrations/versions/") and name.endswith(".py") for name in names
    )
