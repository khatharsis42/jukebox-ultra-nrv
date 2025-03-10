from typing import List
from cachetools.func import ttl_cache
import yt_dlp as youtube_dl
from jukebox.src.backends.search.generic import Search_engine


class Search_engine(Search_engine):
    @classmethod
    @ttl_cache(ttl=3600 * 24)  # 24h
    def url_search(cls, query: str) -> List[dict]:
        results = []
        with youtube_dl.YoutubeDL(cls.ydl_opts) as ydl:
            metadata = ydl.extract_info(query, False)

        if "_type" in metadata and metadata["_type"] == "playlist":
            for res in metadata["entries"]:
                results.append({
                    "source": "soundcloud",
                    "title": res["title"],
                    "artist": res["uploader"],
                    "url": res["webpage_url"],
                    "albumart_url": res["thumbnails"][0]["url"],
                    "album": None,
                    "duration": int(res["duration"]),
                    "id": res["id"]
                })
        else:
            results.append({
                "source": "soundcloud",
                "title": metadata["title"],
                "artist": metadata["uploader"],
                "url": metadata["webpage_url"],
                "albumart_url": metadata["thumbnail"],
                "album": None,
                "duration": int(metadata["duration"]),
                "id": metadata["id"]
            })
        return results

    has_multiple_search = True

    @classmethod
    @ttl_cache(ttl=3600 * 24)  # 24h
    def multiple_search(cls, query: str, use_youtube_dl: bool = True) -> List[dict]:
        results = []

        with youtube_dl.YoutubeDL(cls.ydl_opts) as ydl:
            metadatas = ydl.extract_info("scsearch5:" + query, False)

        for metadata in metadatas["entries"]:
            results.append({
                "source": "soundcloud",
                "title": metadata["title"],
                "artist": metadata["uploader"],
                "url": metadata["webpage_url"],
                "albumart_url": metadata["thumbnail"],
                "album": None,
                "duration": int(metadata["duration"]),
                "id": metadata["id"]
            })
        return results
