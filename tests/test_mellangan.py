from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from doteshi.atlas import mellangan

ROOT = Path("C:/Users/soulwax/Workspace/c++/mellangan")
ATLAS, LAYOUT = ROOT / "res" / "atlas.png", ROOT / "tools" / "atlas_layout.py"
pytestmark = pytest.mark.skipif(not (ATLAS.exists() and LAYOUT.exists()), reason="Mellangan repo not present")


@pytest.fixture(scope="module")
def imported():
    return mellangan.import_atlas(ATLAS, LAYOUT)


def test_rebuild_is_identical(imported):
    image, records = imported
    out = mellangan.rebuild(ATLAS, records)
    assert out.size == image.size and np.array_equal(np.asarray(out), np.asarray(image))


def test_every_cell_has_a_unique_record(imported):
    _, records = imported
    expected = sum(b.columns * b.rows for b in mellangan.bands(LAYOUT))
    assert sum(r["kind"] == "cell" for r in records) == expected
    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids))


def test_free_cells(imported):
    _, records = imported
    free = {r["index"] for r in mellangan.free_cells(records, "jewels")}
    assert {68, 69, 70, 71} <= free and 56 not in free


def test_lock_written(imported, tmp_path):
    image, records = imported
    mellangan.write_lock(records, tmp_path / "m.lock.json", image.size)
    assert (tmp_path / "m.lock.json").stat().st_size > 0
