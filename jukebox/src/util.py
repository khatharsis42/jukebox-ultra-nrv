from functools import wraps

import alsaaudio
from flask import current_app as app
from flask import session, redirect


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session or session['user'] is None:
            return redirect("/auth")
        return f(*args, **kwargs)

    return decorated


def get_mixer_name():
    """

    :returns: Mixer name : either the one in config.py, or if it doesn't exist the first in the list of available mixers.
    """
    if "AMIXER_CHANNEL" in app.config and app.config["AMIXER_CHANNEL"] in alsaaudio.mixers():
        return app.config["AMIXER_CHANNEL"]
    else:
        # app.logger.info(alsaaudio.mixers())
        return alsaaudio.mixers()[0]


def get_volume():
    """
    Example of amixer output :
    Simple mixer control 'Master',0
    Capabilities: pvolume pswitch pswitch-joined
    Playback channels: Front Left - Front Right
    Limits: Playback 0 - 65536
    Mono:
    Front Left: Playback 40634 [62%] [on]
    Front Right: Playback 40634 [62%] [on]
    """
    m = alsaaudio.Mixer(get_mixer_name())
    return int(m.getvolume()[0])


def set_volume(volume):
    try:
        if int(volume) < 0 or int(volume) > 100:
            app.logger.warning("Error, volume {} incorrect".format(volume))
            return
    except ValueError:
        app.logger.warning("Error, volume {} incorrect".format(volume))
        return
    m = alsaaudio.Mixer(get_mixer_name())
    m.setvolume(int(volume))
    app.logger.info("Volume set to %s", get_volume())
