"""Copy the repository's app-assets/ into the package at build time (S12.1)."""

import shutil
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class AppAssetsHook(BuildHookInterface):  # type: ignore[type-arg]
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        root = Path(self.root)
        source = root.parent / "app-assets"
        target = root / "src" / "blueprint" / "app_assets"
        if not source.is_dir():
            raise FileNotFoundError(f"app-assets source directory not found: {source}")
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(source, target)
