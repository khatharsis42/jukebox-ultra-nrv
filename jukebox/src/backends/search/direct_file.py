from typing import List
import youtube_dl
from jukebox.src.backends.search.generic import Search_engine


class Search_engine(Search_engine):
    @classmethod
    def url_search(cls, query: str) -> List[dict]:
        with youtube_dl.YoutubeDL(cls.ydl_opts) as ydl:
            metadata = ydl.extract_info(query, False)
        return [{
            "source": "direct-file",
            "title": metadata["title"],
            "artist": None,
            "album": None,
            "url": query,
            "albumart_url": "https://static.vecteezy.com/system/resources/thumbnails/004/685/239/small/chain-link-hyperlink-icon-isolated-on-white-background-free-free-vector.jpg",
            "duration": 42,  # TODO: trouver le moyen de rentrer une bonne valeur lol
            "id": metadata["id"]}
        ]
