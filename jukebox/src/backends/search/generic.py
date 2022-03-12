import re, requests
from flask import current_app as app
from flask import session

import youtube_dl
import json
from urllib.parse import unquote


def search_engine(query, use_youtube_dl=True):
    results = []
    query = query.strip(" ")
    print(query[:6])
    if query[:6] == "ftp://":
        query = unquote(query)
    #print(query)
    #print("---")

    # We use youtube-dl to get the song metadata
    # only problem : it's a bit slow (about 3 seconds)
    ydl_opts = {
            #'writeinfojson': True,
            'skip_download': True, # we do want only a json file
            #'outtmpl': "tmp_music", # the json is tmp_music.info.json
            'ignoreerrors': True,
            'cachedir': False
            }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        metadata = ydl.extract_info(query, False)

    if "entries" in metadata:
        for res in metadata["entries"]:
            thumbnail = None
            if "thumbnail" in res:
                thumbnail = res["thumbnail"]
            artist = None
            if "artist" in res:
                artist = res["artist"]
            duration = None
            if "duration" in res:
                duration = res["duration"]

            results.append({
                "source": "generic",
                "title": res["title"],
                "artist": None,
                "url": res["url"],
                "albumart_url": thumbnail,
                "duration": duration,
                "id": metadata["id"]
                })
    else:
        thumbnail = None
        if "thumbnail" in metadata:
            thumbnail = metadata["thumbnail"]
        artist = None
        if "artist" in metadata:
            artist = metadata["artist"]
        duration = None
        if "duration" in metadata:
            duration = metadata["duration"]
        url = query
        if "url" in metadata:
            url = metadata["url"]

        results.append({
            "source": "generic",
            "title": metadata["title"],
            "artist": None,
            "url": url,
            "albumart_url": thumbnail,
            "duration": duration,
            "id": metadata["id"]
            })

    return results
