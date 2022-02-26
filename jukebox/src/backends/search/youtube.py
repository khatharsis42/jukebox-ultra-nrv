import re, requests
from flask import current_app as app
from flask import session
import youtube_dl
import json
import isodate


def parse_iso8601(x):
    """Parse YouTube's length format, which is following iso8601 duration."""
    return isodate.parse_duration(x).total_seconds()


def search(query):
    results = []
    youtube_ids = None
    m = re.search("youtube.com/watch\?v=([\w\d\-_]+)", query)
    if m:
        youtube_ids = [m.groups()[0]]
    m = re.search("youtu.be/(\w+)", query)
    if m:
        youtube_ids = [m.groups()[0]]
    # if youtube_ids:
    # app.logger.info("Youtube video pasted by %s: %s", session["user"], youtube_ids[0])
    # else:
    # app.logger.info("Youtube search by %s : %s", session["user"], query)
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "part": "snippet",
            "q": query,
            "key": app.config["YOUTUBE_KEY"],
            "type": "video"
        })
    if r.status_code != 200:
        if r.status_code != 403:
            raise Exception(r.text, r.reason)
        else:
            return search_fallback(query)
    data = r.json()
    if len(data["items"]) == 0:  # Si le serveur n'a rien trouvé
        app.logger.warning("Nothing found on youtube for query {}".format(query))
    youtube_ids = [i["id"]["videoId"] for i in data["items"]]
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "part": "snippet,contentDetails",
            "key": app.config["YOUTUBE_KEY"],
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
            "url": "http://www.youtube.com/watch?v=" + i["id"],
            "albumart_url": i["snippet"]["thumbnails"]["medium"]["url"],
            "duration": parse_iso8601(i["contentDetails"]["duration"]),
            "id": i["id"],
            "album": album,
        })
    return results


def search_engine(query, use_youtube_dl=False, search_multiple=True):
    if use_youtube_dl or "YOUTUBE_KEY" not in app.config or app.config["YOUTUBE_KEY"] is None:
        if search_multiple:
            return search_fallback(query)
        else:
            return search_ytdl_unique(query)
    return search(query)


def search_ytdl_unique(query):
    ydl_opts = {
        'skip_download': True,
    }

    results = []
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        metadata = ydl.extract_info(query, False)

    """
    app.logger.info("Title: {}".format(metadata["title"]))
    app.logger.info("Track: {}".format(metadata["track"]))
    app.logger.info("Alt Title: {}".format(metadata["alt_title"]))
    app.logger.info("Album: {}".format(metadata["album"]))
    app.logger.info("Artist: {}".format(metadata["artist"]))
    app.logger.info("Uploader: {}".format(metadata["uploader"]))
    """

    title = metadata["title"]
    if title is None and metadata["track"] is not None:
        title = metadata["track"]
    artist = None
    if "artist" in metadata:
        artist = metadata["artist"]
    if artist is None and "uploader" in metadata:
        artist = metadata["uploader"]
    album = None
    if "album" in metadata:
        album = metadata["album"]

    results.append({
        "source": "youtube",
        "title": title,
        "artist": artist,
        "album": album,
        "url": query,
        "albumart_url": metadata["thumbnail"],
        "duration": int(metadata["duration"]),
        "id": metadata["id"]
    })
    # app.logger.info("Results : ")
    # app.logger.info(results)
    return results


def search_fallback(query):
    ydl_opts = {
        'skip_download': True,
        'ignoreerrors': True
    }
    # You can find the list of all opts here
    # https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/YoutubeDL.py#L128-L278

    results = []

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        metadatas = ydl.extract_info("ytsearch5:" + query, False)

    for metadata in metadatas["entries"]:
        if metadata is not None:
            """
            app.logger.info("Title: {}".format(metadata["title"]))
            app.logger.info("Track: {}".format(metadata["track"]))
            app.logger.info("Alt Title: {}".format(metadata["alt_title"]))
            app.logger.info("Album: {}".format(metadata["album"]))
            app.logger.info("Artist: {}".format(metadata["artist"]))
            app.logger.info("Uploader: {}".format(metadata["uploader"]))
            """

            title = metadata["title"]
            if title is None and metadata["track"] is not None:
                title = metadata["track"]
            artist = None
            if "artist" in metadata:
                artist = metadata["artist"]
            if artist is None and "uploader" in metadata:
                artist = metadata["uploader"]
            album = None
            if "album" in metadata:
                album = metadata["album"]

            results.append({
                "source": "youtube",
                "title": title,
                "artist": artist,
                "album": album,
                "url": metadata["webpage_url"],
                "albumart_url": metadata["thumbnail"],
                "duration": metadata["duration"],
                "id": metadata["id"]
            })
    return results
