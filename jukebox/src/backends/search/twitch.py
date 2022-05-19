from typing import List
from flask import current_app as app
import yt_dlp as youtube_dl
from jukebox.src.backends.search.generic import Search_engine
from functools import lru_cache


class Search_engine(Search_engine):
    @classmethod
    @lru_cache()
    def url_search(cls, query: str) -> List[dict]:
        # app.logger.info("Query: {}".format(query))
        results = []
        with youtube_dl.YoutubeDL(cls.ydl_opts) as ydl:
            metadata = ydl.extract_info(query, False)

        # app.logger.info(metadata)
        """
        app.logger.info("Title: {}".format(metadata["title"]))
        app.logger.info("Track: {}".format(metadata["track"]))
        app.logger.info("Alt Title: {}".format(metadata["alt_title"]))
        app.logger.info("Album: {}".format(metadata["album"]))
        app.logger.info("Artist: {}".format(metadata["artist"]))
        app.logger.info("Uploader: {}".format(metadata["uploader"]))
        """

        if "title" in metadata:
            title = metadata["title"]
        else:
            title = None
        if "uploader" in metadata:
            artist = metadata["uploader"]
        else:
            artist = None
        album = None

        if "thumbnails" in metadata and len(metadata["thumbnails"]) > 0:
            thumbnail = metadata["thumbnails"][0]
        else:
            thumbnail = None
        results.append({
            "source": "twitch",
            "title": title,
            "artist": artist,
            "album": album,
            "url": query,
            "albumart_url": thumbnail["url"],
            "duration": 42,
            "id": metadata["id"]
        })
        app.logger.info(thumbnail)
        # app.logger.info("Results : ")
        # app.logger.info(results)
        return results
