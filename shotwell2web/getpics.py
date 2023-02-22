#!/usr/bin/env python3

"""
- Get images from shotwell db tagged for website
- Make local dir for linked images
- Link all these images with timestamped linknames
- Make local dir for scaled images
- Scale down all images/links
- Set metadata
- Generate thumbnails
"""

import sys
import re
import copy
import sqlite3
import logging
from pathlib import Path

from slugify import slugify
from exiftool import ExifToolHelper

from PIL import Image
# from PIL.Image import Exif
# from PIL.ExifTags import TAGS

from . import constants

log = logging.getLogger(__name__)


def db_connect(dbfile):
    """
    Establish shotwell sqlite db connection
    """
    if not dbfile:
        log.error("No dbfile given. Aborting.")
        sys.exit(1)

    connection = sqlite3.connect(dbfile)
    return connection


def get_shotwell_thumb_ids(*, tag, dbfile):
    """
    Get shotwell photo ids for given tag by querying the shotwell sqlite db.
    In shotwell, the prefix “thumb” denotes a photo, “video” a video.
    """
    thumb_ids = None
 
    dbparams = {
        "tag": tag,
        "col": "photo_id_list",
        "table_name": "TagTable",
    }

    sql = f'SELECT {dbparams["col"]} FROM {dbparams["table_name"]} WHERE name =:tag'

    cursor = db_connect(dbfile).cursor()
    cursor.execute(sql, dbparams)
    thumb_ids = cursor.fetchall()
    # [('thumb0000000000000b0d,thumb00...9,thumb0000000000003647,',)]
    thumb_ids = thumb_ids[0]
    # ('thumb0000000000000b0d,thumb000...c9,thumb0000000000003647,',)
    thumb_ids = thumb_ids[0]
    thumb_ids = thumb_ids.split(",")

    return thumb_ids


def get_shotwell_photo_ids(thumb_ids):
    """
    Convert shotwell thumb_id to photo_id.
    Basically: thumb_id='thumb0000000000003ecf' -> photo_id=16079
    """
    photo_ids = []
    valid_pattern = re.compile(r"^thumb(\w){16}$")

    for thumb_id in thumb_ids:
        if valid_pattern.match(thumb_id):
            thumb_id = thumb_id.replace("thumb", "")
            photo_id = int(thumb_id, base=16)
            photo_ids.append(photo_id)

    photo_ids.sort()
    return photo_ids


def get_photo_paths(shotwell_photo_ids, dbfile=None):
    """
    Get filesystem paths for shotwell photo ids by query the shotwell sqlite db; eg.:
    shotwell_photo_id=21221 -> photo_path='/path/to/photofiles/20151201.jpg'
    """
    paths = []
    db_table = "PhotoTable"
    db_column = "filename"

    cursor = db_connect(dbfile).cursor()

    for shotwell_photo_id in shotwell_photo_ids:
        sql = f'SELECT {db_column} FROM {db_table} WHERE id={shotwell_photo_id}'
        cursor.execute(sql)
        photo_path = cursor.fetchone()
        photo_path = photo_path[0]
        paths.append(photo_path)

    return paths


#
# Image information and manipulation
#

# def get_exif(file_name) -> Exif:
#     exif = None
#     try:
#         image: Image.Image = Image.open(file_name)
#         exif = image.getexif()
#     except UnidentifiedImageError as e:
#         print(f"Got UnidentifiedImageError: {e}")
#     return exif

# def get_exif_ifd(exif):
#     if not exif: return
#     for key, value in TAGS.items():
#         # print(f"{key=}, {value=}")
#         if value == "ExifOffset":
#             break
#     info = exif.get_ifd(key)
#     info_dict = {
#         TAGS.get(key, key): value
#         for key, value in info.items()
#     }
#     timestamp = info_dict.get("DateTimeOriginal")
#     return timestamp

# def print_metadata(filepath):
#     filepath = str(filepath)
#     with ExifToolHelper() as et:
#         for d in et.get_metadata(filepath):
#             for k, v in d.items():
#                 print(f"Dict: {k} = {v}")


def get_metadata(filepath, tag):
    filepath = str(filepath)
    with ExifToolHelper() as et:
        # print(f"{filepath=}, {et=}")
        for d in et.get_metadata(filepath):
            return d.get(tag)


def set_metadata(filepath, metadata_dict):
    filepath = str(filepath)
    with ExifToolHelper() as et:
        # Strip all metadata:
        et.execute(
            "-overwrite_original",
            "-all=",
            filepath
        )

        et.set_tags(
            filepath,
            tags=metadata_dict,
            params=["-overwrite_original",]
        )


def to_size_tuple(sizes_as_str):
    """
    Convert given sizes from string to a tuple of width and height:
    '178, 100' -> (178, 100)
    """
    return tuple(int(size) for size in sizes_as_str.split(","))


def get_image_renditions(orig_path, rendition):
    """
    Saves an image redition image file and returns an image rendition object 
    for a given input image file path:
    '/orig/path/dcp_4404.jpg' 
    -> 
    {
        'filename': '20040228172648.jpg',
        'title': 'Colmar',
        'lg': {
            'size_max': (1280, 960),
            'width': 640,
            'height': 960
        },
        'sm': {
            'size_max': (178, 100),
            'width': 67,
            'height': 100
        }
    }
    """
    with Image.open(orig_path) as img:
        actual_rendition = {}

        _filename = rendition.get("filename")
        _metadata_dict = rendition.get("metadata_dict")
        _title = rendition.get("title")

        actual_rendition.update({
            "filename": _filename,
            "title": _title,
        })

        for size in rendition.get("sizes"):
            _size_slug = size.get("size_slug")
            _size_max = to_size_tuple(size.get("size_max"))
            _new_path = constants.IMG_DIR_SCALED / _size_slug / _filename
            _new_path.parent.mkdir(parents=True, exist_ok=True)

            img.thumbnail(_size_max)
            img.save(_new_path, "JPEG", quality=95)  
            set_metadata(_new_path, _metadata_dict)

            width, height = img.size

            actual_rendition.update({
                _size_slug: {
                    "size_max": _size_max,
                    "width": width,
                    "height": height,
                }
            })

        return actual_rendition


def process_images(user_config, paths):
    """
    TODO: refactor
    """
    actual_renditions = []
    paths_count = len(paths)

    metadata_tags = {
        "EXIF:Artist": user_config.photographer_name,
        "EXIF:OwnerName": user_config.photographer_name,
        "EXIF:Copyright": f"© {user_config.photographer_name}, all rights reserved.",
        "XMP:Creator": user_config.photographer_name,
        "XMP:CreatorWorkURL": user_config.photographer_www,
        "XMP:CreatorWorkEmail": user_config.photographer_email,
        "XMP:Credit": f"© {user_config.photographer_name}, all rights reserved.",
    }

    for index, orig_path in enumerate(paths, start=1):

        if user_config.process_n_photos and index > user_config.process_n_photos:
            log.warning("Only processing %s images, as requested via 'process_n_photos' in your ini file.", user_config.process_n_photos)
            return actual_renditions

        # print_metadata(orig_path)
        _orig_createdata = get_metadata(orig_path, "EXIF:CreateDate")
        _orig_title = get_metadata(orig_path, "XMP:Title")
        metadata_dict = copy.deepcopy(metadata_tags)

        if _orig_title:
            metadata_dict.update({"XMP:Title": _orig_title})

        _timestamp = slugify(_orig_createdata, separator="")
        scaled_filename = f"{_timestamp}.jpg"

        requested_renditions = {
            "filename": scaled_filename,
            "title": _orig_title,
            "metadata_dict": metadata_dict,
            "sizes": [
                {
                    "size_slug": "lg",
                    "size_max": user_config.img_size_lg,
                },
                {
                    "size_slug": "sm",
                    "size_max": user_config.img_size_sm,
                },
            ],
        }

        actual_renditions.append(
            get_image_renditions(orig_path, requested_renditions)
        )

        _orig_path_segments = "/".join(Path(orig_path).parts[-3:])
        log.info(f'* {index:03}/{paths_count:03}: {_orig_path_segments} -> {scaled_filename}')

    return actual_renditions


def main(user_config):
    """
    Prepare image files for html gallery stage.
    """
    _shotwell_db_file = Path(user_config.shotwell_db_path)
    shotwell_thumb_ids = get_shotwell_thumb_ids(tag=user_config.tag, dbfile=_shotwell_db_file)
    shotwell_photo_ids = get_shotwell_photo_ids(shotwell_thumb_ids)

    photo_paths = get_photo_paths(shotwell_photo_ids, dbfile=_shotwell_db_file)

    log.info(f"Found {len(photo_paths)} photos for tag `{user_config.tag}` in shotwell db `{_shotwell_db_file}`")
    # with open(result_list_path, "w") as outfile:
    #     outfile.write("\n".join(photo_paths))

    renditions = process_images(user_config, photo_paths)

    return renditions
