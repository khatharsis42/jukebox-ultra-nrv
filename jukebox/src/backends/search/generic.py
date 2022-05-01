from typing import List


class Search_engine:
    ydl_opts = {
        'skip_download': True,
    }
    # You can find the list of all opts here
    # https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/YoutubeDL.py#L128-L278
    @classmethod
    def url_search(cls, query: str) -> List[dict]:
        """Takes in a url, returns the result. For certain search engines, the list may be
        longer than 1 because it was a playlist URL.

        :param query: The query. Better if is an url, else it might not mork as intented.
        :returns: List of tracks as dict. The list may be of length 1 if it's a direct URL, or 0 if the URL is invalid.
        """
        raise Exception("Method not yet implemented")
        return [{}]
    has_multiple_search = False
    @classmethod
    def multiple_search(cls, query: str, use_youtube_dl: bool = True) -> List[dict]:
        """
        Takes in a query (aka keywords), returns the result of the search.

        :param query: The query.
        :param use_youtube_dl: Boolean indicating if the search should be conducted using youtube-dl.
        Almost always true.
        :returns: List of tracks found as dict.
        """
        raise Exception("Method not yet implemented")
        return [{}]
