from pathlib import Path
import logging


PROJECT_DIR = Path( __file__ ).parent.parent.absolute()
LOGLEVEL = logging.INFO

PUBLIC_DIR = PROJECT_DIR / "public"
STATIC_SRC_DIR = PROJECT_DIR / "static"
STATIC_PUBLIC_DIR = "assets"
IMG_DIR_SCALED = PUBLIC_DIR / "img"
