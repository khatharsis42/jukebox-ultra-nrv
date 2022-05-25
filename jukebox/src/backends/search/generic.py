from cachetools.func import ttl_cache
from typing import List


# noinspection PyUnreachableCode
class Search_engine:
    """
    Une classe utilisée pour modéliser un moteur de recherche pour différentes plateformes.
    Chaque plateforme possède son moteur de recherche qui s'appelle Search_engine et qui hérite de ce Search_engine.
    Possède deux méthodes, url_search permettant d'importer une musique depuis une URL,
    et multiple_search, permettant de faire une recherche à partir de mots-clefs.
    """
    ydl_opts = {
        'skip_download': True,
    }

    # You can find the list of all opts here
    # https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/YoutubeDL.py#L128-L278
    @classmethod
    @ttl_cache(ttl=3600 * 24)  # 24h
    def url_search(cls, query: str) -> List[dict]:
        """Takes in a url, returns the result. For certain search engines, the list may be
        longer than 1 because it was a playlist URL.

        :param query: The query. Better if is an url, else it might not mork as intended.
        :returns: List of tracks as dict. The list may be of length 1 if it's a direct URL, or 0 if the URL is invalid.
        """
        raise MethodNotImplemented("Method not yet implemented")
        return [{}]

    has_multiple_search = False

    @classmethod
    @ttl_cache(ttl=3600 * 24)  # 24h
    def multiple_search(cls, query: str, use_youtube_dl: bool = True) -> List[dict]:
        """
        Takes in a query (aka keywords), returns the result of the search.
        NOT ALWAYS IMPLEMENTED, MAY RAISE A :class:`MethodNotImplemented` EXCEPTION.
        Check implementation with the has_multiple_search boolean.

        :param query: The query.
        :param use_youtube_dl: Boolean indicating if the search should be conducted using youtube-dl. Almost always true.
        :returns: List of tracks found as dict.
        """
        raise MethodNotImplemented("Method not yet implemented")
        return [{}]


class MethodNotImplemented(Exception):
    """An exception for when the method hasn't been implemented yet."""
    pass
