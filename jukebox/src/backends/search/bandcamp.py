from typing import List

import youtube_dl

from jukebox.src.backends.search.generic import Search_engine


class Search_engine(Search_engine):
    @classmethod
    def url_search(cls, query: str) -> List[dict]:
        """
        Search for a bandcamp url.
        """
        results = []
        with youtube_dl.YoutubeDL(cls.ydl_opts) as ydl:
            json_info = ydl.extract_info(query, False)

        # If we have a playlist
        if "_type" in json_info and json_info["_type"] == "playlist":
            for res in json_info["entries"]:
                results.append({
                    "source": "bandcamp",
                    "title": res["track"],
                    "artist": res["artist"],
                    "album": res["album"],
                    "url": res["webpage_url"],
                    "albumart_url": res["thumbnails"][0]["url"],
                    "duration": int(res["duration"]),
                    "id": res["id"]
                })

        # It's a single music
        else:
            results.append({
                "source": "bandcamp",
                "title": json_info["track"],
                "artist": json_info["artist"],
                "album": json_info["album"],
                "url": query,
                "albumart_url": json_info["thumbnail"],
                "duration": int(json_info["duration"]),
                "id": json_info["id"]
            })
        return results
