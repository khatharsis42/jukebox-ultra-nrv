import threading

from flask import Blueprint, request, jsonify

from jukebox.src.Track import Track
from jukebox.src.util import *

playlist = Blueprint('playlist', __name__)

length: str
needs_to_update = True


def set_to_update():
    global needs_to_update
    needs_to_update = True


@playlist.route("/add", methods=['POST'])
@playlist.route("/add/<ident>", methods=["POST"])
@requires_auth
def add(ident: int = None):
    """
    Ajoute une musique à la playlist. Les informations de la musique sont stockées dans la requête POST, ou bien dans l'URL de la page.
    Le dictionnaire de la requête POST vient généralement de la recherche de musique.
    NB : cela permet de modifier la requête POST et de jouer n'importe quelle audio sur le Jukebox;

    Dans le cas spécifique de l'ajout d'une musique depuis sa page de statistiques, il était plus simple de récupérer son ID depuis l'URL.
    Les informations sont alors extraites depuis la BDD.

    :param ident: Optionel, utilisé ssi n'est pas None (valeur par défaut). L'ID de la musique dans la BDD.
    """
    track_dict: dict
    if ident is not None:
        track_dict = Track.import_from_id(app.config["DATABASE_PATH"], ident).serialize()
        # Gotta serialize it for it to be a dict
    else:
        track_dict = request.form.to_dict()
    app.logger.info("Adding track %s", track_dict["url"])
    track = check_track_in_database(track_dict)
    if track is not None and not track.obsolete and not track.blacklisted:
        app.logger.info(track)
    else:
        if ident is not None:
            return redirect(f"/statistics/track/{ident}")
        return "nok"
    add_track(track.serialize())
    set_to_update()
    if ident is not None:
        return redirect(f"/statistics/track/{ident}")
    return "ok"


def add_track(track: dict):
    """Fonction subalterne permettant d'ajouter une track.

    :param track: Une musique représentée par un dictionnaire (ie :class: `Track` sérialisée).
    """
    with app.playlist_lock:
        track["user"] = session["user"]
        app.playlist.append(track)
        if len(app.playlist) == 1:
            threading.Thread(target=app.player_worker).start()


def check_track_in_database(track_dict: dict) -> Track:
    """
    Cherche si la track est dans la BDD. Sinon, l'insère dans la BDD.

    :param track_dict: Un dictionnaire représentant une track.
    :returns: Une :class: `Track` correspondant à la musique, importée depuis la BDD.
    """
    with app.database_lock:
        if not Track.does_track_exist(app.config["DATABASE_PATH"], track_dict["url"]):
            Track.insert_track(app.config["DATABASE_PATH"], track_dict)
        else:
            # we refresh the track in database
            Track.refresh_by_url(app.config["DATABASE_PATH"], track_dict["url"])
        return Track.import_from_url(app.config["DATABASE_PATH"], track_dict["url"])


@playlist.route("/remove", methods=['POST'])
@requires_auth
def remove():
    """Supprime une track de la playlist. La track est identifiée par son ID et son RandomID, stockée dans la requête POST."""
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
                set_to_update()
                return "ok"
    app.logger.info("Track " + track["url"] + " not found !")
    return "nok"


@playlist.route("/volume", methods=['POST'])
@requires_auth
def volume():
    """Setter pour la volume, la valeur est stockée dans la requête POST."""
    if request.method == 'POST':
        set_volume(request.form["volume"])
        return "ok"


@playlist.route("/suggest")
def suggest():
    """Renvoie une liste suggestion depuis la BDD. Sélectionne d'abord une musique parmis celles existantes,
    puis sélectionne un log pour choisir l'utilisateur qui sera affiché.

    :returns: JSON de 5 musiques recommandées existant déjà dans la BDD.
    """
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
                app.logger.warning("Was going to put an obsolete track in the recommendation")
                track.set_obsolete_value(app.config["DATABASE_PATH"], True)
    return jsonify(result)


def get_length() -> str:
    """
    Fonction qui renvoie une string représentant le temps restant dans la playlist.
    Pour des raisons de performances, utilise la variable `needs_to_update` afin de ne se mettre à jour que quand la playlist est modifiée.

    :returns: String, sous la forme `{heures}h {minutes}m {secondes}s` la plus restreinte possible.
    """
    global length, needs_to_update
    if not needs_to_update:
        return length
    needs_to_update = False
    track: dict
    sum = 0
    for track in app.playlist[1:]:
        sum += int(track['duration'])
    if sum == 0:
        length = ""
    elif sum < 60:
        length = f"{sum:02}s"
    elif sum // 60 < 60:
        length = f"{sum // 60}m{sum % 60:02d}s"
    else:
        length = f"{sum // 60 // 60}h{(sum // 60) % 60}m{sum % 60:02}s"
    return length
