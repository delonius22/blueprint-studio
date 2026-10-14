"""The vendored runtime prompts shipped as package data (SPECS S12, MODEL-CONNECTION.md).

The files are copied verbatim from the repository's ``app-assets/`` at build
time, loaded once at startup and never written at runtime.
"""

from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

from blueprint.errors import StartupError

ASSET_FILES = (
    "interviewer-instructions.md",
    "course-context.md",
    "design-judge-reviewer.md",
    "design-judge-merge.md",
    "to-spec.md",
    "to-tickets.md",
    "LICENSE-mattpocock-skills.txt",
)


class AssetError(StartupError):
    """A vendored asset is missing or empty."""


@dataclass(frozen=True)
class Assets:
    interviewer_instructions: str
    course_context: str
    design_judge_reviewer: str
    design_judge_merge: str
    to_spec: str
    to_tickets: str
    license: str


def packaged_assets_dir() -> Traversable:
    return files("blueprint") / "app_assets"


def load_assets(root: Traversable | Path | None = None) -> Assets:
    """Load every asset, refusing (naming the file) if one is missing or empty."""
    directory = packaged_assets_dir() if root is None else root
    texts: list[str] = []
    for name in ASSET_FILES:
        path = directory / name
        if not path.is_file():
            raise AssetError(f"app-assets file {name} is missing")
        text = path.read_bytes().decode("utf-8")
        if not text.strip():
            raise AssetError(f"app-assets file {name} is empty")
        texts.append(text)
    return Assets(*texts)
