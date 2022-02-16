# import threading

import mpv


def log_mpv(logger):
    """"
    A function that takes a logging function, and converts it into another logging function
    that is usable by the python-mpv module. This is dufully inspired by the GitHub page of
    python-mpv, feel free to check it out.

    :param logger: a logger, meaning you call it with a string as an argument in order to log something
    """

    def f(loglevel, component, message):
        logger('[python-mpv] {}: {}'.format(component, message))

    return f


class MyMPV(mpv.MPV):
    def __init__(self, argv, log_handler=None, video=False):
        super().__init__(video=video, log_handler=log_mpv(log_handler))  # , start_event_thread=False)

        self.playlist_pos = 0
        self.ended = False
