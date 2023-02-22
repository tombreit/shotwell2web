import logging
import sys

from . import constants


logging.basicConfig(
    stream=sys.stdout,
    level=constants.LOGLEVEL,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
