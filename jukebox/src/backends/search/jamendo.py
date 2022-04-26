import re, requests
from flask import current_app as app
from flask import session

import youtube_dl
import json


def search_engine(query, use_youtube_dl=True):
    results = []

    # We use youtube-dl to get the song metadata
    # only problem : it's a bit slow (about 3 seconds)
    ydl_opts = {
            # 'writeinfojson': True,
            'skip_download': True,  # we do want only a json file
            # 'outtmpl': "tmp_music", # the json is tmp_music.info.json
            }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        metadata = ydl.extract_info(query, False)
    # app.logger.info(metadata)
    try:
        album = metadata["album"]
    except KeyError:
        album = None
    duration = metadata["duration"]
    if duration is None:
        # app.logger.info("Duration is None")
        duration = 42  # Arbitrary value because youtube-dl is broken

    results.append({
        "source": "jamendo",
        "title": metadata["track"],
        "artist": metadata["artist"],
        "album": album,
        "url": query,
        "albumart_url": metadata["thumbnail"],
        "duration": duration,
        "id": metadata["id"]
        })
    return results
