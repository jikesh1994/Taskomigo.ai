"""Versioned prompt templates.

Each prompt lives in two files, `<name>.v<N>.system.txt` and `<name>.v<N>.user.txt`.
A behaviour change means a new version file (old versions stay for reproducibility),
and every AI-generated record stores the `Prompt.id` that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from string import Template

_DIR = Path(__file__).parent


@dataclass(frozen=True, slots=True)
class Prompt:
    name: str
    version: int
    system: str
    user_template: str

    @property
    def id(self) -> str:
        return f"{self.name}@v{self.version}"

    def render(self, **values: str) -> str:
        # $-placeholders; missing values raise, so a template typo can't ship silently.
        return Template(self.user_template).substitute(values)


@cache
def load_prompt(name: str, version: int) -> Prompt:
    base = _DIR / f"{name}.v{version}"
    return Prompt(
        name=name,
        version=version,
        system=Path(f"{base}.system.txt").read_text(encoding="utf-8").strip(),
        user_template=Path(f"{base}.user.txt").read_text(encoding="utf-8").strip(),
    )
