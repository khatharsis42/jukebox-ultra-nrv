# -*- coding: utf-8 -*-
import threading
import time

import logging

import mpv
from flask import Flask

from jukebox.src.MyMPV import MyMPV
from jukebox.src.Track import Track
from jukebox.src.main import main
from jukebox.src.auth import auth
from jukebox.src.playlist import playlist, set_to_update

import importlib


class Jukebox(Flask):
    """
    Flask application for the Jukebox.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)
        with open("version.txt", 'r') as f:
            self.version = f.read()

        self.mpv = None
        self.currently_played: dict = None
        self.last_played: dict = None
        self.number_of_repeats: int = 0

        self.mpv_lock = threading.Lock()
        self.database_lock = threading.Lock()
        self.stylesheet = "default.css"
        self.config.from_pyfile("../config.py")
        self.register_blueprint(main)
        self.register_blueprint(auth)
        self.register_blueprint(playlist)

        self.playlist_lock = threading.Lock()
        self.playlist = []
        self.player_skip = threading.Event()
        self.player_time = 0

        # Load backends

        self.search_backends = []
        for i in self.config["SEARCH_BACKENDS"]:
            self.search_backends.append(importlib.import_module("jukebox.src.backends.search." + i))
        self.search_cache: dict = {}
        self.cache_size = 500

    def player_worker(self):
        """
        Function called in a separate thread managing the mpv player.
        """
        while len(self.playlist) > 0:
            set_to_update()
            is_repeating = False
            if self.last_played is not None:
                # If there is a possible track be could have skipped
                if self.last_played["actual_length"] < 0.1 * self.last_played["duration"] \
                        and self.number_of_repeats <= 5:
                    # And we didn't actually play it
                    # Yeah idk 5 seems like a good number
                    # On a besoin de ça, parce que sinon deux musiques qui sautent l'une après l'autre
                    # et boum ça boucle infiniment
                    # NB : j'ai pas d'idée de meilleure implémentation opur éviter les skips
                    # Mais ça marche très bien pour le moment, donc pas forcément besoin d'améliorer
                    # Au pire, si les skips sont trop fréquents, il y a deux fix:
                    #       1 - Augmenter le numéro maximal de check
                    #       2 - Vider le cache de youtube-dl après chaque échec
                    #           (parait que ça marche, à checker)
                    app.logger.info("Time elapsed since the beginning of the last track too short.")
                    app.logger.info(f"Time Elapsed :{self.last_played['actual_length']} ; Last Track Duration : {self.last_played['duration']}")
                    # Basically, if not enough time has passed since the last track
                    # It's because we skipped the music, and we need to put it once again
                    self.number_of_repeats += 1
                    self.playlist.insert(0, app.last_played)
                    is_repeating = True
                else:
                    self.number_of_repeats = 0
            url = self.playlist[0]["url"]
            user = self.playlist[0]["user"]
            start_time = time.time()
            self.currently_played = self.playlist[0]
            with app.mpv_lock:
                if hasattr(self, 'mpv') and self.mpv:
                    del self.mpv
                self.mpv = MyMPV(None, log_handler=app.logger.info)  # we start the track
            with self.database_lock:
                track = Track.import_from_url(app.config["DATABASE_PATH"], url)
                if not is_repeating:
                    track.insert_track_log(app.config["DATABASE_PATH"], user)
            with app.mpv_lock:
                self.mpv.play(url)
            # L'instruction "mpv.wait_for_playback()" doit être sans lock
            # Sinon segfault
            # NB : un ancien maintainer a dit cela, mais on a encore des crashs du Core de MPV
            # d'où le try...except
            # L'ancien maintainer avait proposé d'utililser les playlists mpv
            # Mais de facto c'est compliqué si mpv crash...

            try:
                self.mpv.wait_for_playback()  # it's stuck here while it's playing
            except mpv.ShutdownError:
                app.logger.warning("MPV core crashed, it happens.")
                # Vu qu'on relance une instance de MPV à chaque nouvelle track
                # Et qu'on check maintenant les skips
                # Eh bien on a pas besoin de relancer le core...
                # Mais c'est quand même intéressant de savoir qu'il a crashé

                # Les lignes pour relancer MPV que j'ai commenté:
                # self.mpv.stop()
                # self.mpv = MyMPV(None, log_handler=app.logger.info)

            with self.mpv_lock:
                del self.mpv
            with self.playlist_lock:
                if len(self.playlist) > 0:  # and url == self.currently_played:
                    del self.playlist[0]

            self.currently_played["actual_length"] = time.time() - start_time
            self.last_played = self.currently_played
        self.number_of_repeats = 0
        self.last_played = None


app = Jukebox(__name__)
