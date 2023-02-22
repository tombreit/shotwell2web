"""
Entrypoint for our shotwell2web script.
"""

import configparser
import sys
import json
import logging
from dataclasses import dataclass

from .htmlbuilder import main as htmlbuilder


log = logging.getLogger(__name__)


if __name__ == '__main__':

    try:
        config = configparser.ConfigParser()
        CONFIG_FILENAME = 'shotwell2web.ini'
        with open(CONFIG_FILENAME, encoding="utf-8") as f:
            config.read_file(f)
    except FileNotFoundError as file_not_found_error:
        log.critical(
            "Config file not found: %s. See README.md for hints. Exiting.", file_not_found_error
        )
        sys.exit(1)


    @dataclass
    class UserConfig:
        """
        Quick and dirty pass around our configparser values as a dataclass.
        TODO: Automate the instanciation of UserConfig
        """
        tag: str
        shotwell_db_path: str
        process_n_photos: int
        title: str
        photographer_name: str
        photographer_email: str
        photographer_www: str
        legal_link: list
        privacy_policy_link: list
        img_size_lg: tuple
        img_size_sm: tuple

    user_config = UserConfig(
        tag = config["PhotoSrc"]["tag"],
        shotwell_db_path = config["PhotoSrc"]["shotwell_db_path"],
        process_n_photos = int(config["PhotoSrc"]["process_n_photos"]),
        img_size_lg = config["ImageRenditions"]["img_size_lg"],
        img_size_sm = config["ImageRenditions"]["img_size_sm"],
        title = config["Website"]["title"],
        photographer_name = config["Website"]["photographer_name"],
        photographer_email = config["Website"]["photographer_email"],
        photographer_www = config["Website"]["photographer_www"],
        legal_link = json.loads(config["Website"]["legal_link"]),
        privacy_policy_link = json.loads(config["Website"]["privacy_policy_link"]),
    )

    htmlbuilder(user_config)
