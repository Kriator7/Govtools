from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.config import PROJECT_ROOT


def render_template(channel: str, name: str, context: dict) -> str:
    root = PROJECT_ROOT / "templates" / channel
    env = Environment(
        loader=FileSystemLoader(str(root)),
        autoescape=select_autoescape(disabled_extensions=("txt", "j2")),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(name)
    return template.render(**context).strip()
