"""CI workflow consistency: the release must execute the full pipeline.

design-pipeline.yml's NOTEBOOK_ORDER is the source of truth; release.yml
carries a copy (a tag-triggered workflow can't read another workflow's
env). A stale copy silently ships a partial design snapshot — and, via
the Zenodo GitHub integration, archives it under a permanent DOI.
"""

from pathlib import Path

import pytest
import yaml

from conftest import REPO_ROOT

WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _notebook_order(workflow: str) -> list[str]:
    doc = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
    return doc["env"]["NOTEBOOK_ORDER"].split()


def test_release_runs_same_notebooks_as_pipeline():
    assert _notebook_order("release.yml") == _notebook_order("design-pipeline.yml")


@pytest.mark.parametrize("workflow", ["design-pipeline.yml", "release.yml"])
def test_notebook_order_covers_every_notebook(workflow):
    order = _notebook_order(workflow)
    on_disk = {p.stem for p in Path(REPO_ROOT / "notebooks").glob("*.ipynb")}
    assert len(order) == len(set(order)), "duplicate notebook in NOTEBOOK_ORDER"
    assert set(order) == on_disk
