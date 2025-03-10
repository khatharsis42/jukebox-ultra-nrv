import requests
from typing import List

from flask import current_app as app
import yt_dlp as youtube_dl
import isodate
from cachetools.func import ttl_cache
from jukebox.src.backends.search.generic import Search_engine


class Search_engine(Search_engine):
    ydl_opts = {
        'skip_download': True,
        'ignoreerrors': True,
        'cachedir': False,
        'noplaylist': True
        # Je sais pas s'il faudrait le laisser en True ou le passer en False
        # Il faudrait faire des test...
    }

    @classmethod
    @ttl_cache(ttl=3600 * 24)  # 24h
    def url_search(cls, query: str, use_youtube_dl=True) -> List[dict]:
        if "list" in query:
            return cls.multiple_search(query, search_playlist=True)
        # On est obligé de modifier l'URL, parce que sinon youtube-dl et l'API font n'importe quoi
        id_and_other_shit: List[str]
        if "youtu.be" in query:
            id_and_other_shit = ["v=" + query.split("/")[-1].split("?")[0]]
            try:
                id_and_other_shit += query.split("/")[-1].split("?")[1].split("&")
            except IndexError:
                pass
        else:
            id_and_other_shit = query.split("?")[-1].split("&")
        query = "https://youtube.com/watch?" + id_and_other_shit[0]
        # for x in id_and_other_shit[1:]:
        #     if x[:2] == "t=":
        #         query += "&" + x
        # TODO: En décommentant ce code, on aurait la possibilité de mettre des timestamps dans les musiques
        #       Le problème, c'est que ça risque de poser des problèmes dans la BDD
        #       Notamment parce qu'on risquerait de mettre des musiques avec timestamp dans la BDD
        #       Et donc on risquerait de recommander une musique avec un timestamp
        #       ce qui serait plutôt drôle x) Mais assez frustrant aussi...
        return cls.search_ytdl_unique(query)

    has_multiple_search = True

    @classmethod
    def multiple_search(cls, query: str, search_playlist=False, use_youtube_dl: bool = False) -> List[dict]:
        if use_youtube_dl or "YOUTUBE_KEYS" not in app.config or not app.config["YOUTUBE_KEYS"]:
            return cls.__search_fallback(query, search_playlist=search_playlist)
        return cls.__search(query, search_playlist=search_playlist)

    @classmethod
    def __parse_iso8601(cls, x):
        """Parse YouTube's length format, which is following iso8601 duration."""
        return isodate.parse_duration(x).total_seconds()

    @classmethod
    def __ytdl_metadata_to_dict(cls, query: str, metadata: dict):
        return_dict = {
            "source": "youtube",
        }
        if "title" in metadata and metadata["title"] is not None:
            return_dict["title"] = metadata["title"]
        elif "track" in metadata and metadata["track"] is not None:
            return_dict["title"] = metadata["track"]
        if "artist" in metadata and metadata["artist"] is not None:
            return_dict["artist"] = metadata["artist"]
        elif "uploader" in metadata and metadata["uploader"] is not None:
            return_dict["artist"] = metadata["uploader"]
        if "album" in metadata:
            return_dict["album"] = metadata["album"]
        else:
            return_dict["album"] = None
        if "thumbnail" in metadata:
            return_dict["albumart_url"] = metadata["thumbnail"]
        if "duration" in metadata:
            return_dict["duration"] = int(metadata["duration"])
        else:
            return_dict["duration"] = 0
        if "id" in metadata:
            return_dict["id"] = metadata["id"]
            return_dict["url"] = "https://www.youtube.com/watch?v=" + metadata["id"]

        return return_dict

    @classmethod
    @ttl_cache(ttl=3600 * 24)  # 24h
    def search_ytdl_unique(cls, query: str):
        results = []
        with youtube_dl.YoutubeDL(cls.ydl_opts) as ydl:
            metadata = ydl.extract_info(query, False)
        results.append(cls.__ytdl_metadata_to_dict(query, metadata))
        return results

    @classmethod
    @ttl_cache(ttl=3600 * 24)  # 24h
    def __search(cls, query, search_playlist=False):
        app.logger.info("Using YoutubeAPI like a chad")
        results = []
        for key in app.config["YOUTUBE_KEYS"]:
            r: requests.models.Response
            if search_playlist:
                params = {
                    "playlistId": query.split("list=")[-1].split("&")[0],
                    "key": key,
                    "part": "snippet",
                    "maxResults": 50
                }
                r = requests.get(
                    "https://www.googleapis.com/youtube/v3/playlistItems",
                    params=params
                )
            else:
                params = {
                    "part": "snippet",
                    "key": key,
                    "type": "video",
                    "maxResults": 5,
                    "q": query
                }
                r = requests.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params=params
                )
            if r.status_code != 200:
                if r.status_code != 403:
                    raise Exception(r.text, r.reason)
                else:
                    # On essaye la clef suivante
                    continue
            data = r.json()
            if len(data["items"]) == 0:  # Si le serveur n'a rien trouvé
                app.logger.warning("Nothing found on youtube for query {}".format(query))
            youtube_ids: List[str]
            if not search_playlist:
                youtube_ids = [i["id"]["videoId"] for i in data["items"]]
            else:
                youtube_ids = [i["snippet"]["resourceId"]["videoId"] for i in data["items"]]
            r = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,contentDetails",
                    "key": key,
                    "id": ",".join(youtube_ids)
                })
            data = r.json()
            for i in data["items"]:
                album = None
                # app.logger.info(i)
                results.append({
                    "source": "youtube",
                    "title": i["snippet"]["title"],
                    "artist": i["snippet"]["channelTitle"],
                    "url": "https://www.youtube.com/watch?v=" + i["id"],
                    "albumart_url": i["snippet"]["thumbnails"]["medium"]["url"],
                    "duration": cls.__parse_iso8601(i["contentDetails"]["duration"]),
                    "id": i["id"],
                    "album": album,
                })
            return results
        # Si on arrive ici c'est qu'on a pas réussi à obtenir quoi que ce soit avec
        # Les clefs, donc on fait le fallback
        return cls.__search_fallback(query, search_playlist=search_playlist)

    @classmethod
    @ttl_cache(ttl=3600 * 24)  # 24h
    def __search_fallback(cls, query, search_playlist=False):
        app.logger.info("Using youtube-dl like a virgin")
        results = []
        if search_playlist:
            ydl_opts = cls.ydl_opts.copy()
            ydl_opts.pop("noplaylist")
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                metadatas = ydl.extract_info(query, False)
        else:
            with youtube_dl.YoutubeDL(cls.ydl_opts) as ydl:
                metadatas = ydl.extract_info("ytsearch5:" + query, False)

        for metadata in metadatas["entries"]:
            if metadata is not None:
                results.append(cls.__ytdl_metadata_to_dict(query, metadata))
        return results
