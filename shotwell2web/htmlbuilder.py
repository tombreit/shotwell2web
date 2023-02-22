#!/usr/bin/env python3

import shutil
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from . import constants
from .getpics import main as getpics

log = logging.getLogger(__name__)


def cleanup(directory) -> None:
    """
    Clean up generated static data files from previous runs
    and re-add static assets (eg. photoswipe)
    """
    log.info("Cleanup directory %s...", directory)

    if directory.is_dir():
        shutil.rmtree(directory)

    Path(directory).mkdir(parents=True, exist_ok=True)

    # Copy static website
    static_public_dir_path = constants.PUBLIC_DIR / constants.STATIC_PUBLIC_DIR
    shutil.copytree(constants.STATIC_SRC_DIR, static_public_dir_path, dirs_exist_ok=True)


def render(template_name, context, directory=None):
    """
    Jinja2 render helper.
    """
    loader = FileSystemLoader(directory) if directory else FileSystemLoader('templates')
    env = Environment(loader=loader)
    template = env.get_template(template_name)
    return template.render(context)


def generate_html(*, renditions=None, user_config):
    """
    Render a html image gallery for given image renditions/files.
    """
    log.info("Running generate_html for %s renditions...", len(renditions))

    template = "index.html"
    output_file = constants.PUBLIC_DIR / "index.html"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    context = {
        "renditions": renditions,
        "config": user_config,
        "static_dir": constants.STATIC_PUBLIC_DIR,
    }
    object_html = render(template, context)

    with open(output_file, 'w', encoding="utf-8") as file:
        file.write(object_html)

    log.info("Done. Generated photo gallery for %s renditions", len(renditions))
    log.info("Your gallery: 'file://%s'", output_file)


def main(user_config) -> None:
    """
    Get and prepare image files and render a html gallery.
    """
    cleanup(constants.PUBLIC_DIR)
    generate_html(renditions=getpics(user_config), user_config=user_config)
