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
from jukebox.src.playlist import playlist

import importlib


class Jukebox(Flask):
    """
    Flask application for the Jukebox
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

        self.admins = ["Khatharsis"]
        self.premiums = ["Kaname",
                         "Khatharsis",
                         "Legendarian",
                         "Akasuna",
                         "Mar",
                         "Alternatif",
                         "Biscuit",
                         "Chloe",
                         "Typhlos",
                         "Flegmatik",
                         "Yrax",
                         "PtiBouchon",
                         ]
        self.user_add_limits = {"local": 100000}
        self.user_rem_limits = {"local": 0}

    def player_worker(self):
        """
        Function called in a separate thread managing the mpv player.
        """
        while len(self.playlist) > 0:
            is_repeating = False
            if self.last_played is not None:
                if self.last_played["actual_length"] < 0.1 * self.last_played["duration"] \
                        and self.number_of_repeats <= 5:
                    # Yeah idk 5 seems like a good number
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
            # the next instruction should be the only one without a lock
            # but it causes a segfault when there is a lock
            # I fear fixing it may be dirty
            # we could switch to mpv playlists though
            try:
                self.mpv.wait_for_playback()  # it's stuck here while it's playing
            except mpv.ShutdownError:
                app.logger.info("MPV core crashed, it happens.")
                # Sometimes the core crashes, so we gotta relaunch it
                # I have no idea where it comes from
                # EDIT : Since we know try to play the track again in the next iteration,
                # These lines do not do anything
                # So i commented them out
                # self.mpv.stop()
                # self.mpv = MyMPV(None, log_handler=app.logger.info)
            """
            if counter == max_count and end - start < min(track.duration, min_duration) and track.source == "youtube":
                # we mark the track as obsolete
                track.set_obsolete_value(app.config["DATABASE_PATH"], 1)
                app.logger.info("Marking track {} as obsolete".format(track.url))
            """

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
