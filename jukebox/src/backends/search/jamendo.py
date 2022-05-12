from typing import List
from functools import lru_cache
import youtube_dl
from jukebox.src.backends.search.generic import Search_engine


class Search_engine(Search_engine):
    @classmethod
    @lru_cache()
    def url_search(cls, query: str) -> List[dict]:
        with youtube_dl.YoutubeDL(cls.ydl_opts) as ydl:
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

        return [{
            "source": "jamendo",
            "title": metadata["track"],
            "artist": metadata["artist"],
            "album": album,
            "url": query,
            "albumart_url": metadata["thumbnail"],
            "duration": duration,
            "id": metadata["id"]}
        ]
