import youtube_dl
import json


def search_engine(query, use_youtube_dl=True):
    ydl_opts = {
        'skip_download': True,  # we do want only a json file
        }
    results = []

    # We use youtube-dl to get the song metadata
    # only problem : it's a bit slow (about 3 seconds)
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
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


def search_multiples(query):
    ydl_opts = {
            'skip_download': True,
            }
    results = []

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
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
