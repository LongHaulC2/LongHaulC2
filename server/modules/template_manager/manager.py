import os
import tomllib
from pathlib import Path

import structlog

server_logger = structlog.getLogger("server")

workspace_dir = os.getenv("WORKSPACE_DIR", "/var/lib/longhaulc2")
TEMPLATES_DIR = Path(workspace_dir) / "implant_templates"


class TemplateManager:
    _cache: dict[str, dict] | None = None

    @classmethod
    def _scan(cls) -> dict[str, dict]:
        templates = {}
        if not TEMPLATES_DIR.exists():
            server_logger.warning("Templates directory not found", path=str(TEMPLATES_DIR))
            return templates

        for entry in TEMPLATES_DIR.iterdir():
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            desc_path = entry / "desc.toml"
            if not desc_path.exists():
                continue
            try:
                with Path.open(desc_path, "rb") as f:
                    desc = tomllib.load(f)
                template_info = desc.get("template", {})
                template_info["build"] = desc.get("build", {})
                template_info["dir_name"] = entry.name
                templates[entry.name] = template_info
            except Exception as e:
                server_logger.error("Failed to parse desc.toml", path=str(desc_path), error=e)

        return templates

    @classmethod
    def get_all(cls) -> list[dict]:
        if cls._cache is None:
            cls._cache = cls._scan()
        return list(cls._cache.values())

    @classmethod
    def get_by_name(cls, name: str) -> dict | None:
        if cls._cache is None:
            cls._cache = cls._scan()
        return cls._cache.get(name)

    @classmethod
    def get_template_dir(cls, name: str) -> Path | None:
        info = cls.get_by_name(name)
        if not info:
            return None
        return TEMPLATES_DIR / info["dir_name"]

    @classmethod
    def invalidate_cache(cls):
        cls._cache = None
