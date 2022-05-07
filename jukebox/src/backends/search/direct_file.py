from typing import List
from flask import session
from flask import current_app as app
from tinytag import TinyTag
import requests
import os
from tinytag.tinytag import TinyTagException
from jukebox.src.backends.search.generic import Search_engine


class Search_engine(Search_engine):
    @classmethod
    def url_search(cls, query: str) -> List[dict]:
        # On est obligé de télécharger la musique pour pouvoir obtenir ses métadonnées
        # En réalité, vu que c'est une requête, c'est relativement rapide
        filename = app.config["TEMP_DOWNLOAD_PATH"]+query.split("/")[-1]
        open(filename, 'wb+').write(requests.get(query, allow_redirects=False).content)
        if filename.split(".")[-1] == "webm":
            # Then we gotta convert it cause webm ain't supported round these parts
            command = f"ffmpeg -i {filename} -y {filename.rsplit('.', maxsplit=1)[0]}.mp3"
            os.system(command)
            os.remove(filename)
            filename = filename.rsplit('.', maxsplit=1)[0] + ".mp3"
        track_dict = {"source": "direct-file"}
        try:
            track = TinyTag.get(filename, image=True)
            track_dict["title"] = track.title if track.title is not None else query.split("/")[-1]
            track_dict["artist"] = track.artist if track.artist is not None else session["user"]
            # TODO: pas forcément la meilleure idée, mais bon en vrai c'est logique dans un sens
            track_dict["album"] = track.album
            track_dict["url"] = query
            track_dict["albumart_url"] = track.get_image() if track.get_image() is not None \
                else "https://cdn.searchenginejournal.com/wp-content/uploads/2020/08/404-pages-sej-5f3ee7ff4966b-760x400.png"
            # TODO: Trouver un moyen plus propre de faire ça.
            #       Idée: Prendre la première frame, la sauvegarder quelque part
            #       L'utilisateur la récupère avec une url ?
            #       À méditer...
            track_dict["duration"] = int(track.duration)
            track_dict["id"] = track.__hash__()
        except TinyTagException as e:
            print(e)
        os.remove(filename)
        return [track_dict]
