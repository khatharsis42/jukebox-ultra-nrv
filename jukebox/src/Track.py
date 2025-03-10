import random
import sqlite3
import sys

import requests
from youtube_dl import DownloadError

from jukebox.src.backends.search.generic import Search_engine
import jukebox.src.backends.search as search_backends
from jukebox.src.util import *


class Track:
    """
    Une classe représentant une musique. Possède les mêmes attributs que dans la base de donnée, dans ta table track_info.
    """

    def __init__(self,
                 ident: int, url: str, track: str, artist: str, source: str, albumart_url: str,
                 album: str = None, duration=None, blacklisted: bool = False,
                 obsolete: bool = False, user=None):
        """
        :param ident: L'identifiant de la musique dans la BDD.
        :param url: L'URL de la musique. Est passée en argument à mpv pour jouer la musique.
        :param track: Titre.
        :param artist: Artiste.
        :param source: Source.
        :param albumart_url: URL vers la vignette de la musique.
        :param album: Album (?).
        :param duration: Durée de la musique en secondes.
        :param blacklisted: Indique si la musique est blacklistée.
        :param obsolete: Indique si la musique est obsolète.
        :param user: Peut être None, indique l'utilisateur ayant ajouté la musique.
        """
        self.ident = ident
        self.url = url
        self.track = track
        self.artist = artist
        self.source = source
        self.albumart_url = albumart_url
        self.album = "" if album is None else album
        self.duration = duration
        self.blacklisted = blacklisted
        self.obsolete = obsolete
        self.user = user

    def __str__(self):
        if self.ident is None:
            ret = "None: "
        else:
            ret = str(self.ident) + ": "
        if self.url is None:
            ret = ret + "None"
        else:
            ret = ret + self.url
        return ret

    @classmethod
    def does_track_exist(cls, database, url):
        """
        NB: Les musiques sont groupées par similitude de nom, à cause d'un bug différentiant une musique en HTTP d'une musique en HTTPS.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :param url: URL de la musique.
        :return: True si une musique avec l'URL correspondant existe.
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        # check if track not in track_info i.e. if url no already there
        c.execute("""
            SELECT id 
            FROM track_info 
            WHERE url = ?
            ;""",
                  (url,)
                  )
        r = c.fetchall()
        return len(r) > 0
        # the following block is used to manage cases http and https
        """
        if len(r) > 0:
            return True
        else:  # basically, we want to consider that http://url = https://url
            if url[:5] == "http:":
                url = url[:4] + 's' + url[4:]
            else:
                url = url[:4] + url[5:]
            c.execute(""""""select id
                         from track_info
                         where url = ?;"""
        """,
                      (url,))
            r = c.fetchall()
            return len(r) > 0
            """

    @classmethod
    def import_from_id(cls, database: str, ident: int):
        """
        Permet de récupérer une musique depuis son ID.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :param ident: ID de la musique.
        :returns: La track, si elle existe, sinon None.
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        app.logger.info(f"Getting the stats for {ident}")
        c.execute("SELECT * FROM track_info WHERE id = ?;", (ident,))
        r = c.fetchone()
        if r is None:
            return None
        # assert r[0] == ident
        return Track(ident=r[0], url=r[1], track=r[2], artist=r[3],
                     album=r[4], duration=r[5], albumart_url=r[6],
                     source=r[7], blacklisted=r[8], obsolete=r[9])

    @classmethod
    def import_from_name(cls, database: str, ident):
        """
        Permet de récupérer une musique depuis son nom. Renvoie un tableau des :class:`Track` possèdant ce nom.

        :param database: Path vers base de donnée. Généralement app.config["DATABASE_PATH"].
        :param ident: Nom de la musique.
        :returns: List[Track] : la track, si elle existe, sinon None.
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        app.logger.info(f"Getting the stats for {ident}")
        c.execute("SELECT * FROM track_info WHERE track = ?;", (ident,))
        table = c.fetchall()
        if table is None:
            return None
        # assert r[0] == ident
        return [Track(ident=r[0], url=r[1], track=r[2], artist=r[3],
                      album=r[4], duration=r[5], albumart_url=r[6],
                      source=r[7], blacklisted=r[8], obsolete=r[9]) for r in table]

    @classmethod
    def import_from_url(cls, database: str, url: str):
        """
        Permet de récupérer une musique depuis son URL. Ce dernier étant unique, une seule :class:`Track` est renvoyée.

        :param database: Path vers base de donnée. Généralement app.config["DATABASE_PATH"].
        :param url: URL de la musique.
        :returns: List[Track] : la track, si elle existe, sinon None.
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("SELECT * FROM track_info WHERE url = ?;",
                  (url,))
        r = c.fetchone()
        if r is None:
            return None
        return Track(ident=r[0], url=r[1], track=r[2], artist=r[3],
                     album=r[4], duration=r[5], albumart_url=r[6],
                     source=r[7], blacklisted=r[8], obsolete=r[9])

    @classmethod
    def get_random_track(cls, database):
        """
        Renvoie une :class:`Track` de manière aléatoire.
        La probabilité est uniforme sur les tracks (modulo les problèmes de HTTTP/HTTPS).
        Un log est ensuite choisi de manière aléatoire pour trouver une personne ayant ajouté cette musique.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :returns: Une Track.
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("""
            SELECT * \
            FROM track_info \
            WHERE blacklisted != 1 AND obsolete != 1\
            ORDER BY RANDOM() \
            LIMIT 1 \
            """)
        r = c.fetchone()
        if r is None:  # no track in database
            return None
        track = Track(ident=r[0], url=r[1], track=r[2], artist=r[3],
                      album=r[4], duration=r[5], albumart_url=r[6],
                      source=r[7], blacklisted=r[8], obsolete=r[9])
        c.execute("""
            SELECT user \
            FROM users, log \
            WHERE users.id = log.userid \
                AND log.trackid = ? \
            ORDER BY RANDOM() \
            LIMIT 1;""",
                  (track.ident,))
        r = c.fetchone()
        if r is not None:
            track.user = r[0]
        return track

    @classmethod
    def insert_track(cls, database: str, track_form: dict):
        """
        Insère une :class:`Track` dans la base de donnée à partir d'un dictionnaire.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :param track_form: Dictionnaire contenant les clefs "url","title","artist","album","duration","albumart_url" et "source".
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("""
            INSERT INTO track_info \
            (url, track, artist, album, duration, albumart_url, source) \
            VALUES \
            (?  ,     ?,      ?,     ?,        ?,            ?,      ?); \
            """,
                  (track_form["url"], track_form["title"], track_form["artist"],
                   track_form["album"], track_form["duration"],
                   track_form["albumart_url"], track_form["source"]))
        conn.commit()

    @classmethod
    def refresh_by_url(cls, database, url):
        """
        Rafraichit les métadonnées d'une musique dans la BDD depuis son URL.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :param url: URL de la musique.
        :returns: La track actualisée si possible.
        """
        # Check if we even have it
        track = cls.import_from_url(database, url)
        if track is None:
            return None
        # check if source is loaded
        if 'jukebox.src.backends.search.' + track.source not in sys.modules:
            return track
        if track.source == "youtube":
            try:
                track_dict = search_backends.youtube.Search_engine.url_search(url)[0]
            except DownloadError as e:
                app.logger.warning(f"DownloadError : {e}")
                if "403" not in e.args[0]:
                    # Je part du principe que s'il y a une DownloadError, c'est que la track est obsolete
                    # Il faut cependant pas que cette erreur soit une 403 pour les vidéos YouTube
                    # Parce que cette erreur ne veux en fait rien dire (elle peut arriver de manière random)
                    app.logger.warning("This track couldn't be refreshed, so we're marking it as obsolete.")
                    track.set_obsolete_value(database, True)
                return None
        else:
            try:
                Engine: Search_engine = getattr(search_backends, track.source).Search_engine
                track_dict = Engine.url_search(url)[0]
            except DownloadError as e:
                app.logger.warning("This track couldn't be refreshed, so we're marking it as obsolete.")
                Track.set_obsolete_value(track, database, True)
                return None
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("""
            UPDATE track_info
            SET
                track = ?, \
                artist = ?, \
                albumart_url = ?, \
                album = ?, \
                duration = ?, \
                obsolete = ? \
            WHERE url = ?;
            """,
                  (track_dict["title"],
                   track_dict["artist"],
                   track_dict["albumart_url"],
                   track_dict["album"],
                   track_dict["duration"],
                   0,
                   url)
                  )
        conn.commit()
        return cls.import_from_url(database, url)

    def check_obsolete(self):
        """
        Une méthode rapide pour vérifier l'obsolescence d'une :class:`Track`.
        Vérifie simplement si l'`albumart_url` est existant est ne renvoie pas une erreur 404.
        """
        # TODO: Cette méthode fonctionne pour les vidéos YouTubes, mais pas pour certaines autre sources, il me semble.
        return (self.albumart_url is None or requests.get(self.albumart_url).status_code == 404) if self.source == "youtube" else False

    def set_obsolete_value(self, database: str, obsolete: bool = True):
        """
        Marque la musique comme obsolete ou pas dans la BDD. Change également la valeur de `self.obsolete`.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :param obsolete: True si on veut marquer la track comme obsolete, False sinon.
        """
        app.logger.info(f"Marking track [id = {self.ident}, url = {self.url}] as {'' if obsolete else 'non-'}obsolete")
        self.obsolete = obsolete
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("""
            UPDATE track_info \
            SET obsolete = ? \
            WHERE id = ?""",
                  (self.obsolete, self.ident))
        conn.commit()

    def insert_track_log(self, database: str, user: str):
        """
        Créé un log dans la BDD. Change également la valeur de `self.user`.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :param user: Nom de l'utilisateur.
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        self.user = user
        c.execute("SELECT id FROM users WHERE user = ?;",
                  (user,))
        r = c.fetchall()
        user_id = r[0][0]
        c.execute("INSERT INTO log(trackid,userid) VALUES (?,?)",
                  (self.ident, user_id))
        conn.commit()

    def serialize(self):
        """
        Sérialiseur pour les :class:`Track`. Rajoute un randomid pour différencier deux Tracks identiques dans la playlist.

        :returns: Dictionnaire ayant les clefs "id", "url", "title", "artist", "source", "albumart_url", "album", "duration", "blaklisted", "obsolete", "user", et "randomid".
        """
        return {
            'id': self.ident,
            'url': self.url,
            'title': self.track,
            'artist': self.artist,
            'source': self.source,
            'albumart_url': self.albumart_url,
            'album': self.album,
            'duration': self.duration,
            'blacklisted': self.blacklisted,
            'obsolete': self.obsolete,
            'user': self.user,
            # to identify each track in the playlist
            # even if they have the same url
            'randomid': random.randint(1, 999_999_999_999)
        }

    @classmethod
    def getTrackCounts(cls, database: str, nbr: int, date=0, user=None):
        """
        Renvoie une liste des :class:`Track` de taille `nbr` groupées par nom (`self.title`).
        La liste est triée d'abord par nombre de passage (ie nombre de logs), puis par date d'ajout (plus récent en premier).
        Il est possible de restreindre à une période temporelle avec l'argument `date`.

        NB: Les musiques sont groupées par similitude de nom, à cause d'un bug différentiant une musique en HTTP
        d'une musique en HTTPS. L'ID est donc choisi au hasard.


        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :param nbr: Taille maximale de la liste en sortie.
        :param date: Date, permet de faire des stats journalières et hebdomadaires.
        :return: Liste de (Titre, Nombre de passage, ID).
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        if user:
            command = """
                SELECT track, count(track), track_info.id\
                FROM  track_info, log, users \
                WHERE log.trackid = track_info.id \
                    and log.userid = users.id \
                    and log.time > ? and users.user = ?\
                GROUP BY track_info.track order by count(trackid) DESC, log.id DESC \
                """
            c.execute(command, (date, user,))
        else:
            command = """
                SELECT track, count(track), track_info.id \
                FROM  track_info, log \
                WHERE log.trackid = track_info.id and log.time > ? \
                GROUP BY track_info.track order by count(trackid) DESC, log.id DESC \
                """
            c.execute(command, (date,))
        r = c.fetchall()
        if r is None:
            return None
        if nbr < 0:
            return r
        else:
            return r[:nbr]

    @classmethod
    def get_history(cls, database: str, nbr: int):
        """
        Renvoie l'historique des `nbr` dernières musiques passées sur le jukebox.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :param nbr: Nombre de musiques que l'on veut passer.
        :return: list of (Track_name, track_id, user)
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        command = """
                SELECT track_info.track, track_info.id, users.user \
                FROM  track_info, log, users \
                WHERE \
                    log.userid = users.id \
                    AND log.trackid = track_info.id \
                ORDER BY log.time DESC \
                LIMIT ?
                """
        c.execute(command, (nbr,))
        r = c.fetchall()
        if r is None:
            return None
        else:
            return r
