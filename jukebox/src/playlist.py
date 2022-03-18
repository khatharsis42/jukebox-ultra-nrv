import requests
from flask import Blueprint, request, jsonify, url_for

from jukebox.src.Track import Track
from jukebox.src.util import *
import threading

playlist = Blueprint('playlist', __name__)


@playlist.route("/add", methods=['POST'])
@playlist.route("/add/<ident>", methods=["POST"])
@requires_auth
def add(ident: int = None):
    """
    Adds a song to the playlist. Song information are stored in request.form.to_dict(). This dict generally comes from
    the search.
    In the special case of adding a song to the queue from the stats page, I couldn't find the way to store the
    information in a form, so the optional parameter ident is thus used.

    :param ident: Optional, used iff it isn't None. The id of a song.
    """
    track_dict: dict
    if ident is not None:
        track_dict = Track.import_from_id(app.config["DATABASE_PATH"], ident).serialize()
        # Gotta serialize it for it to be a dict
    else:
        track_dict = request.form.to_dict()
    app.logger.info("Adding track %s", track_dict["url"])
    # track["user"] = session["user"]
    with app.database_lock:
        if not Track.does_track_exist(app.config["DATABASE_PATH"], track_dict["url"]):
            Track.insert_track(app.config["DATABASE_PATH"], track_dict)
        else:
            # we refresh the track in database
            Track.refresh_by_url(app.config["DATABASE_PATH"], track_dict["url"])
        track = Track.import_from_url(app.config["DATABASE_PATH"], track_dict["url"])
        if track is not None and not track.obsolete and not track.blacklisted:
            track.user = session['user']
            app.logger.info(track)
        else:
            return "nok"

    add_track(track)
    if ident is not None:
        return redirect(f"/statistics/track/{ident}")
    return "ok"


def add_track(track: Track):
    with app.playlist_lock:
        track: dict = track.serialize()
        # track["user"] = session["user"]
        app.playlist.append(track)
        if len(app.playlist) == 1:
            threading.Thread(target=app.player_worker).start()


@playlist.route("/remove", methods=['POST'])
@requires_auth
def remove():
    """supprime la track de la playlist"""
    track = request.form
    with app.playlist_lock:
        for track_p in app.playlist:
            if track_p["randomid"] == int(track["randomid"]):
                if app.playlist.index(track_p) == 0:
                    app.logger.info("Removing currently playing track")
                    with app.mpv_lock:
                        app.currently_played["duration"] = 0
                        # Sinon problème
                        app.mpv.quit()
                else:
                    app.playlist.remove(track_p)
                return "ok"
    app.logger.info("Track " + track["url"] + " not found !")
    return "nok"


@playlist.route("/volume", methods=['POST'])
@requires_auth
def volume():
    if request.method == 'POST':
        set_volume(request.form["volume"])
        return "ok"


@playlist.route("/suggest")
def suggest():
    n = 5  # number of songs to display in the suggestions
    if "n" in request.args:
        n = int(request.args.get("n"))
    result = []
    nbr = 0
    while nbr < n:
        # we use a while to be able not to add a song
        with app.database_lock:
            track = Track.get_random_track(app.config["DATABASE_PATH"])
        if track is None:
            # On voudrais pas ajouter une track qui vaut None
            # Cependant, si elle vaut none, ça veut dire une chose :
            # il y a rien dans la db
            # d'où le nbr ++
            nbr += 1
        elif track.blacklisted == 0 \
                and track.obsolete == 0 \
                and track.source in app.config["SEARCH_BACKENDS"]:
            if not track.check_obsolete():
                result.append(track.serialize())
                nbr += 1
            else:
                app.logger.info("Was going to put an obsolete track in the recommendation")
                app.logger.info(f"Marking track [id = {track.ident}, url = {track.url}] as obsolete")
                track.set_obsolete_value(app.config["DATABASE_PATH"], 1)
    return jsonify(result)
