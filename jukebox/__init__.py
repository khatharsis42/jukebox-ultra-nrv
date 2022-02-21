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
        self.currently_played = None
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

    def player_worker(self, user):
        """
        Function called in a separate thread managing the mpv player.
        """
        while len(self.playlist) > 0:
            url = self.playlist[0]["url"]
            self.currently_played = url
            with app.mpv_lock:
                if hasattr(self, 'mpv') and self.mpv:
                    del self.mpv
                self.mpv = MyMPV(None, log_handler=app.logger.info)  # we start the track
            start = time.time()
            end = start
            with self.database_lock:
                track = Track.import_from_url(app.config["DATABASE_PATH"], url)
                track.insert_track_log(app.config["DATABASE_PATH"], user)
            max_count = 10
            min_duration = 2
            counter = 0
            # this while is a little hack, as sometimes, mpv fails mysteriously but work fine on a second or third track
            # so we check that enough time has passed between play start and end
            while counter < max_count \
                    and track.duration is not None \
                    and end - start < min(track.duration, min_duration):  # 1 is not enough
                # note for the future : what if track is passed with a timestamp ? It could be nice to allow it.
                # note from the future : Rather than parsing for a timestamp, I've made it possible to
                # go to a timestamp in the Web UI, so it's actually pretty close.
                start = time.time()
                with app.mpv_lock:
                    self.mpv.play(self.currently_played)
                # the next instruction should be the only one without a lock
                # but it causes a segfault when there is a lock
                # I fear fixing it may be dirty
                # we could switch to mpv playlists though
                try:
                    self.mpv.wait_for_playback()  # it's stuck here while it's playing
                except mpv.ShutdownError:
                    app.logger.info("MPV got shutdown, relaunching the core")
                    # Sometimes the core crashes, so we gotta relaunch it
                    # I have no idea where it comes from
                    self.mpv.stop()
                    self.mpv = MyMPV(None, log_handler=app.logger.info)
                end = time.time()
                counter += 1
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


app = Jukebox(__name__)
