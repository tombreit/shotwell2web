# shotwell2web

*Build a web image gallery from a [Gnome Shotwell](https://wiki.gnome.org/Apps/Shotwell) image database. See it in action on [photography.thms.de](https://photography.thms.de/)*

🖼 What this python script does: 

1. Query shotwell sqlite database for a given tag
1. Get tagged images, resizes, set image metadata
1. Generate a html image gallery for these images
1. The generated 'static bundle'/'public directory' is self-contained, [photoswipe-enabled](https://photoswipe.com/) and could be served via filesystem or via webserver


## 🧻 Requirements

* Python3
* Phil Harvey’s `exiftool` (will be used by `pyexiftool`)
* Shotwell instance with tagged photos


## 🔧 Configuration

This python script expects an `ini` file named `shotwell2web.ini` in the project root directory: 

```ini
[PhotoSrc]
# tag: Supports only one tag to query for
tag = MyPhotoTag
shotwell_db_path = /path/to/.local/share/shotwell/data/photo.db

# For testing, limit the number of photos which will be processed.
# Leave empty to process all photos.
process_n_photos = 3

[Website]
# These strings end up in image metadata and in html
title = Photography
photographer_name = John Doe
photographer_email = mail@example.org
photographer_www = https://example.org
legal_link = ["Legal", "https://example.org/legal.html"]
privacy_policy_link = ["Privacy Policy", "https://example.org/privacy.html"]

[ImageRenditions]
# The - maximum - image dimensions for thumbnails (`_sm`) and, hm, not-thumbnails (`_lg`)
img_size_lg = 1280, 960
img_size_sm = 178, 100
```

## 🦘 Run

```bash
# initial setup
cd <project-dir>/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# build web gallery
python3 -m shotwell2web

# serve web gallery
python3 -m http.server -d public/
```


## ⚖ Licence

GNU General Public License v3.0


## 👏 Standing on the shoulders of giants


<details>
<summary>
<strong>https://mail.gnome.org/archives/shotwell-list/2020-January/msg00001.html</strong>
</summary>

> Yes they are in the sqlite db file.  Here's a perl routine I use to
> extract the tags from the sqlite so I can save them elsewhere; it uses
> the PhotoTable, VideoTable, and TagTable from the sqlite db.  The
> association of a tag to a photo or video is done with the "hexid" in
> the below code, which starts with the string "thumb" for photos and
> the string "video-" for videos.

```perl
# via Perl

sub get_photos {
    my ( $dbh, $verbose ) = @_;

   # exposure_time maps to date/time original field (time of picture's exposure)
    my $select_phototable_sql =
        q{SELECT `id`,`filename`,`rating`,`title`,`exposure_time` }
      . q{FROM `PhotoTable`};
    my $phototable = $dbh->selectall_arrayref($select_phototable_sql);
    print "Found ", scalar(@$phototable), " photos in shotwell
PhotoTable\n" if $verbose;
    $select_phototable_sql =~ s/PhotoTable/VideoTable/;
    my $videotable = $dbh->selectall_arrayref($select_phototable_sql);
    print "Found ", scalar(@$videotable), " videos in shotwell
VideoTable\n" if $verbose;
    my %photos_byhexid = (
        map( (
                sprintf( 'thumb%016x', $_->[0] ),
                [ $_->[1], $_->[2], $_->[3], [], $_->[4] ]
            ),
            @$phototable ),
        map( (
                sprintf( 'video-%016x', $_->[0] ),
                [ $_->[1], $_->[2], $_->[3], [], $_->[4] ]
            ),
            @$videotable )
    );

    my $select_tagtable_sql =
      q{SELECT `name`,`photo_id_list` } . q{FROM `TagTable`};
    my $tagtable = $dbh->selectall_arrayref($select_tagtable_sql);
    print "Found ", scalar(@$tagtable), " tags in shotwell TagTable,
distributing to PhotoTable\n" if $verbose;
    foreach my $row (@$tagtable) {
        my $name = $row->[0];
        $name =~
          s/^\///;    # trim leading / (not sure why it is present in database)
        next unless defined( $row->[1] );    # sometimes a tag is not
        associated with any images
          foreach my $hexid->( split( /,/, $row->[1] ) ){
            die(
                "Error: id $hexid found in TagTable was not found in PhotoTable"
            ) unless exists( $photos_byhexid{$hexid} );
            push( @{ $photos_byhexid{$hexid}[3] }, $name );
          };
    }
    return ( [ sort( { $a->[0] cmp $b->[0] } values(%photos_byhexid) ) ] );

    # returned ref is an array of 5-element arrays:
    # [0]: filename
    # [1]: rating
    # [2]: title (caption)
    # [3]: tag array
    # [4]: date/time
}
```

</details>
<details>
<summary>
<strong>https://strugglers.net/~andy/blog/category/linux/shotwell/</strong>
</summary>

> The photo_id_list column holds the comma-separated list. Each item in the list is of the form:
> - “thumb” or “video-” depending on whether the item is a photo or a video
> - 16 hex digits, zero padded, which is the ID value from the PhotosTable or VideosTable for that item
> - a comma
> Full example of extracting tags for the video file 2019/12/31/20191231_121604.mp4:

```sql
# via sql

$ sqlite3 /home/andy/.local/share/shotwell/DATA/photo.db
SQLite version 3.22.0 2018-01-22 18:45:57
Enter ".help" FOR usage hints.
sqlite> SELECT id
        FROM VideoTable
        WHERE filename LIKE '%20191231%';
553
sqlite> SELECT printf("%016x", 553);
0000000000000229
sqlite> SELECT name
        FROM TagTable
        WHERE photo_id_list LIKE '%video-0000000000000229,%';
/Places
/Places/London
/Places/London/Feltham
/Pets
/Places/London/Feltham/Bedfont Lakes
/Pets/Marge
/Pets/Mandy
```

> If that is not completely clear:
> - The ID for that video file is 553
> - 553 in hexadecial is 229
> - Pad that to 16 digits, add “video-” at the front and “.” at the end (even the last item in the list has a comma at the end)
> - Search for that string in photo_id_list
> - If a row matches then the name column is a tag that is attached to that file

</details>
