import sqlite3
import random
import sys

from youtube_dl import DownloadError

from jukebox.src.util import *


class Track:
    def __init__(self,
                 ident, url, track, artist, source, albumart_url,
                 album=None, duration=None, blacklisted=False,
                 obsolete=0, user=None):
        """

        :param ident: int
        :param url: str
        :param track: str
        :param artist: str
        :param source: str
        :param albumart_url: str
        :param album: str
        :param duration:
        :param blacklisted:
        :param user: may be None, else it means we get it from a log and it is a str
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

        :param database:
        :param url:
        :return: Boolean, True if track exists.
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        # check if track not in track_info i.e. if url no already there
        c.execute("SELECT id FROM track_info WHERE url = ?;",
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
    def import_from_id(cls, database, ident):
        """

        :param database:
        :param ident:
        :return:
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
    def import_from_name(cls, database, ident):
        """

        :param database:
        :param ident:
        :return:
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
    def import_from_url(cls, database, url):
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

        :param database:
        :return: a random track,
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("SELECT * FROM track_info ORDER BY RANDOM() LIMIT 1")
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
    def insert_track(cls, database, track_form):
        """

        :param database:
        :param track_form:
        :return:
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
    def refresh_by_url(cls, database, url, obsolete=0):
        """

        :param database: Database used
        :param url: URL of the track (str)
        :param obsolete: Boolean telling if track is obsolete or not.
        """
        # app.logger.info(url)
        track = cls.import_from_url(database, url)
        if track is None:
            return
        # check if source is loaded
        if 'jukebox.src.backends.search.' + track.source not in sys.modules:
            return
        for search in app.search_backends:
            if search.__name__ == 'jukebox.src.backends.search.' + track.source:
                break
        if track.source == "youtube":
            try:
                track_dict = search.search_engine(
                    url, use_youtube_dl=True, search_multiple=False)[0]
            except DownloadError as e:  # We mark the track as obsolete
                app.logger.info(e.exc_info[1])
                if e.args[0] == "ERROR: This video is unavailable.":
                    track.obsolete = 1
                    track.set_obsolete_value(database, track.obsolete)
                    app.logger.warning(
                        "Marking track {} as obsolete".format(url))
                return
        else:
            track_dict = search.search_engine(url, use_youtube_dl=True)[0]
        # app.logger.info("Track dict : ", track_dict)
        track = Track(None, url, track_dict["title"], track_dict["artist"], track_dict["source"],
                      track_dict["albumart_url"], album=track_dict["album"], duration=track_dict["duration"])
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
                  (track.track,
                   track.artist,
                   track.albumart_url,
                   track.album,
                   track.duration,
                   obsolete,
                   url)
                  )
        conn.commit()
        track = cls.import_from_url(database, url)
        return track

    def set_obsolete_value(self, database, bool=1):
        """

        :param database: Path to the SQLite for the Jukebox
        :param bool: Value of the obsolete column of the track.
        """
        self.obsolete = bool
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("""
            UPDATE track_info \
            SET obsolete = ? \
            WHERE id = ?""",
                  (self.obsolete, self.ident))
        conn.commit()

    def insert_track_log(self, database, user):
        """
        As it creates a log, it also updates the value of self.useré

        :param database:
        :param user:
        :return:
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        self.user = user
        c.execute("SELECT id FROM users WHERE user = ?;",
                  (user,))
        r = c.fetchall()
        # print(r)
        user_id = r[0][0]
        c.execute("INSERT INTO log(trackid,userid) VALUES (?,?)",
                  (self.ident, user_id))
        conn.commit()

    def serialize(self):
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
            'randomid': random.randint(1, 999_999_999_999)
            # even if they have the same url
        }

    @classmethod
    def getTrackCounts(cls, database, nbr, date=0, user=False):
        """
        Returns at most the nbr users with most listening count.
        Tracks are sorted first by count (number of times the track has been added since `date`, and second by most
        recently added.

        :param database:
        :param nbr:
        :param date:
        :return: list of (User, int)
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        if user:
            command = """
                SELECT track, count(track) \
                FROM  track_info, log, users \
                WHERE log.trackid = track_info.id \
                    and log.userid = users.id \
                    and log.time > ? and users.user = ?\
                GROUP BY track_info.track order by count(trackid) DESC, log.id DESC \
                """
            c.execute(command, (date, user,))
        else:
            command = """
                SELECT track, count(track) \
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
