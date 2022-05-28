# import threading

import mpv


def log_mpv(logger):
    """"
    A function that takes a logging function, and converts it into another logging function
    that is usable by the python-mpv module. This is dufully inspired by the GitHub page of
    python-mpv, feel free to check it out.

    :param logger: a logger, meaning you call it with a string as an argument in order to log something

    :returns: A Logging function.
    """

    def f(loglevel, component: str, message: str):
        temp = "\n"
        if message.strip():
            logger(f"[python-mpv]({loglevel}) {component}: {message.rstrip(temp)}")
        # Sinon il y a un \n en trop :shrug:

    return f


class MyMPV(mpv.MPV):
    def __init__(self, config, log_handler=None, video=False):
        if "YOUTUBE_DL_PATH" in config and config["YOUTUBE_DL_PATH"] is not None and config["YOUTUBE_DL_PATH"] != "":
            super().__init__(video=video,
                             log_handler=log_mpv(log_handler),
                             ytdl=True,
                             scripts=f'sponsorblock.lua',
                             script_opts=f'ytdl_hook-ytdl_path={config["YOUTUBE_DL_PATH"]}')
        else:
            super().__init__(video=video,
                             log_handler=log_mpv(log_handler),
                             scripts=f'sponsorblock.lua',)

        self.playlist_pos = 0
        self.ended = False

    def quit(self, code=0):
        super().quit(code=code)
        # Apparement avec code=None ça ne fonctionne pas.
