import random
import re
import datetime
import sys

import flask
from flask import Blueprint, render_template, redirect, session, jsonify, request, flash
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from os import listdir
from os.path import isfile, join

from jukebox.src import playlist
from jukebox.src.User import User
from jukebox.src.util import *
from jukebox.src.Track import Track
from jukebox.src.statistics import create_html_users, create_html_tracks, create_history_tracks
import jukebox.src.backends.search as search_backends

main = Blueprint('main', __name__)


def get_style() -> str:
    """
    Renvoie le nom du thème utilisé par l'utilisateur actuel.
    Dans l'ordre, renvoie d'abord le thème stocké dans le cookie, puis dans la session, puis dans la BDD, et sinon le style de base.

    :returns: String : Le nom du thème.
    """
    cookie = request.cookies.get('style')
    if cookie is not None:
        return cookie
    style: str
    if "stylesheet" in session.keys():
        return session["stylesheet"]
    r = User.getTheme(app.config["DATABASE_PATH"], session["user"])
    if r is not None:
        style = r
    else:
        style = app.stylesheet
    session["stylesheet"] = style
    return style


def get_nav_links():
    """
    Renvoie une liste de tuples (nom, url) des sites affichés dans la barre principale.
    Cette liste est extraite directement du fichier de config.
    """
    if "NAV_LINKS" in app.config:
        return app.config["NAV_LINKS"]
    else:
        return []


@main.route("/app")
@requires_auth
def app_view():
    """
    Renvoie la page principale (accueil.html).
    """
    # app.logger.info("App access from %s", session["user"])
    return render_template("accueil.html",
                           user=session["user"], jk_name=app.config["JK_NAME"],
                           stylesheet=get_style(), navlinks=get_nav_links())


@main.route("/")
def accueil():
    """
    Redirection vers la page principale.
    """
    return redirect("/app")


@main.route("/help")
def help():
    """
    Renvoie la page d'aide.
    """
    # we should add a modules argument to render_template to
    # display which search functions are available
    modules = []
    for i in app.config["SEARCH_BACKENDS"]:
        modules.append(i)
    return render_template("help.html", modules=modules,
                           jk_name=app.config["JK_NAME"],
                           user=session['user'],
                           stylesheet=get_style(), navlinks=get_nav_links(),
                           version=app.version)


@main.route("/settings", methods=['GET', 'POST'])
def settings():
    """Renvoie la page des paramètres. En vérité, cette page sert uniquement à changer le thème.
    """
    # we should add a modules argument to render_template to
    # display which search functions are available

    style_path = "jukebox/static/styles/custom/"
    styles = [(f, f) for f in listdir(style_path) if isfile(
        join(style_path, f)) and f[-4:] == ".css"]

    # app.logger.info(styles)

    class SettingsForm(FlaskForm):
        style = SelectField("Styles", choices=styles)
        submit = SubmitField("Send")

    form = SettingsForm()

    if request.method == 'POST':
        style = request.form["style"]
        session["stylesheet"] = style
        resp: flask.Response = flask.make_response(
            render_template('settings.html', user=session["user"],
                            jk_name=app.config["JK_NAME"], form=form,
                            stylesheet=style, navlinks=get_nav_links()))
        resp.set_cookie('style', style)
        User.setTheme(app.config["DATABASE_PATH"], session["user"], style)
        return resp
    elif request.method == 'GET':
        return render_template('settings.html', user=session["user"],
                               jk_name=app.config["JK_NAME"], form=form,
                               stylesheet=get_style(), navlinks=get_nav_links())


@main.route("/sync")
def sync():
    """
    Fonction appellée par le JS du client pour synchroniser la page.
    Synchronise la playlist, le volume, le timestamp, et le temps restant dans la playlist.

    :returns: JSON des paramètres synchronisés (keys: "playlist", "volume", "time", "playlist_length").
    """
    # TODO: Trouver un moyen d'envoyer l'information de la source, et cacher l'intégration
    #       YouTube si la musique ne vient pas de YouTube. Je dirais qu'il faudrait utiliser
    #       deux variables booléenes dans le JS, afin de savoir si l'utilisateur veut que la
    #       vidéo soit affichée, et si la vidéo peut être affichée.
    #       Aux futurs maintainer de voir comment faire ça.
    volume = get_volume()
    # segfault was here
    with app.mpv_lock:
        if hasattr(app, 'mpv') \
                and app.mpv is not None \
                and hasattr(app.mpv, 'time_pos') \
                and app.mpv.time_pos is not None:
            time_pos = app.mpv.time_pos  # when track is finished, continues augmenting time_pos
        else:
            time_pos = 0
    res = {
        "playlist": app.playlist,
        "volume": volume,
        "time": time_pos,
        "playlist_length": playlist.get_length()
    }

    return jsonify(res)


@main.route("/move-track", methods=['POST'])
@requires_auth
def move_track():
    """
    Traite la requête POST demandant de modifier l'emplacement d'une musique dans la playlist.
    """
    try:
        action = request.form["action"]
        randomid = request.form["randomid"]
    except KeyError:
        return "nok"

    index = None
    with app.playlist_lock:
        for x in app.playlist:
            if str(x["randomid"]) == randomid:
                index = app.playlist.index(x)
                break
        if index is None:
            # app.logger.warning("Track {} not found".format(randomid))
            return "nok"
        if action == "top":
            if index < 2:
                app.logger.warning("Track {} has index".format(index))
                return "nok"
            app.playlist.insert(1, app.playlist.pop(index))
        elif action == "up":
            if index < 2:
                app.logger.warning("Track {} has index".format(index))
                return "nok"
            track_temp = app.playlist[index - 1]
            app.playlist[index - 1] = app.playlist[index]
            app.playlist[index] = track_temp
        elif action == "down":
            if len(app.playlist) - 2 < index or index < 1:
                # app.logger.warning("Track {} has index".format(index))
                return "nok"
            track_temp = app.playlist[index + 1]
            app.playlist[index + 1] = app.playlist[index]
            app.playlist[index] = track_temp
        else:
            return "nok"
    return "ok"


@main.route("/statistics", methods=['GET'])
@requires_auth
def statistics():
    """Renvoie la page de statistiques principale."""
    return render_template('statistics.html', user=session["user"],
                           jk_name=app.config["JK_NAME"],
                           table_users_count_all=create_html_users(
                               app.config["DATABASE_PATH"], nbr=-1),
                           table_users_count_week=create_html_users(app.config["DATABASE_PATH"], nbr=10,
                                                                    date=datetime.datetime.now()
                                                                         - datetime.timedelta(weeks=1)),
                           table_users_count_day=create_html_users(app.config["DATABASE_PATH"], nbr=10,
                                                                   date=datetime.datetime.now()
                                                                        - datetime.timedelta(days=1)),
                           table_tracks_count_all=create_html_tracks(
                               app.config["DATABASE_PATH"], nbr=20),
                           table_tracks_count_week=create_html_tracks(app.config["DATABASE_PATH"], nbr=10,
                                                                      date=datetime.datetime.now()
                                                                           - datetime.timedelta(weeks=1)),
                           table_tracks_count_day=create_html_tracks(app.config["DATABASE_PATH"], nbr=10,
                                                                     date=datetime.datetime.now()
                                                                          - datetime.timedelta(days=1)),

                           stylesheet=get_style(), navlinks=get_nav_links())


@main.route("/statistics/user/<username>", methods=['GET'])
@requires_auth
def user_stats(username: str):
    """Renvoie la page de statistiques pour un utilisateur donné."""
    return render_template('user.html', user=session['user'],
                           jk_name=app.config["JK_NAME"],
                           user_name=username,
                           table_tracks_count_all=create_html_tracks(
                               app.config["DATABASE_PATH"], nbr=20, user=username),
                           table_tracks_count_month=create_html_tracks(
                               app.config["DATABASE_PATH"], nbr=20,
                               date=datetime.datetime.now() - datetime.timedelta(days=30),
                               user=username),
                           stylesheet=get_style(), navlinks=get_nav_links()
                           )


@main.route("/history/<number>", methods=['GET'])
@requires_auth
def history(number: int):
    """
    Renvoie l'historique des number dernières musiques.
    """
    # TODO: Faire un système de pages, plutôt que de juste prendre les n dernières.
    number = int(number)
    # Je déteste python
    # Si on ne fait pas ça, number est une string.
    return render_template('history.html', user=session['user'],
                           jk_name=app.config["JK_NAME"],
                           n=number,
                           table_last_tracks=create_history_tracks(
                               app.config["DATABASE_PATH"], nbr=number),
                           stylesheet=get_style(), navlinks=get_nav_links()
                           )


@main.route("/statistics/track/<track>", methods=['GET'])
@requires_auth
def track_stats(track):
    """Renvoie la page de statisques pour une musique d'ID donné.

    NB: Les musiques sont groupées par similitude de nom, à cause d'un bug différentiant une musique en HTTP d'une musique en HTTPS.
    """
    t: Track = Track.import_from_id(app.config["DATABASE_PATH"], track)
    if not t:
        # This means it's not a real id, but rather a youtube id
        # ie:
        t: Track = Track.import_from_url(app.config["DATABASE_PATH"], "https://www.youtube.com/watch?v=" + track)
        if t:
            return redirect(f"/statistics/track/{t.ident}")
        # Then it's not https but http
        t: Track = Track.import_from_url(app.config["DATABASE_PATH"], "http://www.youtube.com/watch?v=" + track)
        if t:
            return redirect(f"/statistics/track/{t.ident}")
        else:
            return redirect("/app")
    # Ça, c'est pour que si jamais il y a une musique portant le même nom
    # Mais qui est obsolète, et bien c'est pas elle qu'on ajoute.
    # A la place, c'est la première musique non obsolète qu'on ajoute.
    if t.obsolete:
        t_list = Track.import_from_name(app.config["DATABASE_PATH"], t.track)
        random.shuffle(t_list)
        for new_t in t_list:
            new_t = Track.refresh_by_url(app.config["DATABASE_PATH"], new_t.url)
            if new_t is not None and not new_t.obsolete:
                t = new_t

    return render_template('track.html', user=session['user'],
                           jk_name=app.config["JK_NAME"],
                           track=t.track,
                           ident=t.ident,
                           obsolete=t.obsolete,
                           table_users_count_all=create_html_users(
                               app.config["DATABASE_PATH"], nbr=20,
                               track=t.track),
                           stylesheet=get_style(), navlinks=get_nav_links()
                           )


@main.route("/status", methods=['GET'])
def status():
    """Renvoie un JSON indiquant que le portail est UP.

    :returns: {"status" : "UP"} """
    # This is used in the portail.cj interface, to check if this is still up
    res = {
        "status": "UP"
    }
    return jsonify(res)


@main.route("/refresh-track", methods=['POST'])
@requires_auth
def refresh_track():
    """
    Traite la requête POST demandant de rafraichir une track dans la BDD.
    """
    try:
        url = request.form["url"]
    except KeyError:
        return "nok"
    with app.database_lock:
        Track.refresh_by_url(app.config["DATABASE_PATH"], url)
    return "ok"


url_regexes = {
            "youtube": re.compile('^(https?://)?(www.)?(youtube.com|youtu.be)'),
            "jamendo": re.compile('^(https?://)?(www.)?jamendo.com'),
            "twitch": re.compile('^(http://|https://)?(www\.)?twitch.tv'),
            "soundcloud": re.compile('^(http://|https://)?(www.)?soundcloud.com'),
            "bandcamp": re.compile('^(http://|https://)?\S*\.bandcamp.com')
        }
search_regexes = {
    "soundcloud": re.compile('(\!sc\s)|(.*\s\!sc\s)|(.*\s\!sc$)'),
    "youtube": re.compile('(\!yt\s)|(.*\s\!yt\s)|(.*\s\!yt$)')
}
@main.route("/search", methods=['POST'])
@requires_auth
def search():
    """
    Renvoie une liste de tracks correspondant à la requête depuis divers services.

    :returns: Liste de JSON des tracks.
    """
    query = request.form["q"].strip()
    # On veut enlever les trailing whitespace qui resteraient, pour rendre les query plus uniformes
    results = []
    if query in app.search_cache:
        app.logger.info(f"Using the cache for request '{query}'")
        return jsonify(app.search_cache[query])
    # if query is http or https or nothing xxxxxxx.bandcamp.com/
    # then results += apps.search_backends.bandcamp(query)
    # (if bandcamp loaded)
    # similar for soundcloud
    # else we search only on youtube (in the future, maybe soundcloud too
    regex_url = re.compile("(http://|https://)")
    # TODO: Pour être vraiment bien, il faudrait différencier le fait de mettre une URL
    #       et le fait de faire une recherche. Par exemple, si je met une URL sous la forme
    #       https://youtube.com/watch?v=[VideoID], alors ça ajoute directement cette vidéo.
    #       Et si je met !yt [Termes de Recherches] alors ça fait une recherche (avec la base
    #       qui serait YouTube).
    #       ATTENTION :  si on fait ça, il faudrait faire gaffe à la forme de l'URL
    #       Typiquement, les URL avec un timestamp pourraient poser un problème ?
    #       Au moins dans la DB, il faudrait pouvoir faire gaffe à ça.
    #       URL d'exemple :
    #           Doit jouer une seule musique et pas la playlist :
    #               https://www.youtube.com/watch?v=uHrLkddGjFk&list=RDuHrLkddGjFk&start_radio=1
    #           Doit jouer la musique à partir de son timestamp ? Ou pas.
    #               https://youtube/watch?v=EIP3HdFl-JM?t=135
    #           Doit également fonctionner:
    #               https://youtu.be/EIP3HdFl-JM?t=138
    #       Ça permettrait notamment de rajouter de manière pas trop compliquée les musiques custom
    #       i.e. on met l'url d'un fichier .mp3 ou mp4 ou un truc du genre
    #       ça reconnait automatiquement et ça le joue. Avec un point bonus si on arrive à
    #       diffuser la vidéo sur la page en plus de ça.
    used_search = False
    if re.match(regex_url, query) is not None:
        # Then we have an URL boys
        for source, regex in url_regexes.items():
            if re.match(regex, query) is not None and \
                    f'jukebox.src.backends.search.{source}' in sys.modules:
                app.logger.info(f"Importing music from url from {source}.")
                # TODO: Faire une interface pour les search_engine
                # TODO: Faire une interface pour les search_engine avec recherche multiple
                music: dict = getattr(search_backends, source).search_engine(query)[0]
                # TODO: On part du principe que l'URL est valide lol
                track = playlist.check_track_in_database(music)
                playlist.add_track(track.serialize())
                used_search = True
    # Search for multiples tracks
    else:
        for source, regex in search_regexes.items():
            if re.match(regex, query) is not None and \
                    f'jukebox.src.backends.search.{source}' in sys.modules:
                app.logger.info(f"Using {source} search")
                results += getattr(search_backends, source).search_multiples(query[4:])
                used_search = True
    if not used_search and 'jukebox.src.backends.search.youtube' in sys.modules:
        app.logger.info("Using Generic youtube search")
        results += search_backends.youtube.search_multiples(query)
        used_search = True
    if not used_search:
        app.logger.error("Error: no search module found")

    if len(app.search_cache) >= app.cache_size:
        app.search_cache.pop(random.choice(list(app.search_cache.keys())))
    app.search_cache[query] = results
    # TODO: On m'a proposé de faire en sorte qu'on puisse rajouter des résultats
    #       Par exemple, si on n'a pas satisfait des 5 premiers résultats, de cliquer
    #       sur un bouton "Voir plus" et on optiendrait alors les 5 résultats suivants.
    #       À voir comment on mettrait ça en place, une idée possible serait de faire
    #       une fonction search(i) qui rechercherait les i premiers résultats ?
    #       Sinon de manière plus optimisée, faire en sorte que search renvoie un à un
    #       des tracks au client, et ensuite on aurait juste à les traiter.
    #       L'avantage de faire ça, c'est qu'on pourrait avoir les premiers résultats
    #       d'une recherche très rapidement. Le désavantage, c'est que j'ai du mal à voir
    #       comment implémenter ça sans faire de multithreading ? Je ne sais pas trop.
    #       ---> C'est possiblement faisable avec le cache en fait, je suis con moi.
    #       J'ai pas forcément envie de faire ça, je vais peut être le laisser à mon successeur.
    return jsonify(results)


@main.route('/pause_play', methods=['POST'])
def pause():
    """Met la musique en pause, ou bien la relance."""
    app.mpv.command('cycle', 'pause', None)
    return "ok"


@main.route('/rewind', methods=['POST'])
def rewind():
    """Remet la musique en arrière de 10 secondes."""
    app.currently_played["duration"] += 10
    app.mpv.command('seek', - 10, 'relative', None)
    return "ok"


@main.route('/advance', methods=['POST'])
def advance():
    """Avance la musique de 10 secondes."""
    app.currently_played["duration"] -= 10
    app.mpv.command('seek', + 10, 'relative', None)
    return "ok"


@main.route('/jump', methods=['POST'])
def jump():
    """Avance la musique jusqu'au timestamp fourni dans la requête."""
    timestamp = request.form["jump"]
    if timestamp.count(':') == 0:
        time = int(timestamp)
    elif timestamp.count(':') == 1:
        minutes, secondes = [int(t) for t in timestamp.split(":")]
        time = 60 * minutes + secondes
    elif timestamp.count(':') == 2:
        hours, minutes, secondes = [int(t) for t in timestamp.split(":")]
        time = 60 * (60 * hours + minutes) + secondes
    else:
        return "nok"
    app.currently_played["duration"] -= time
    # The "duration" field of the currently played song has to be changed,
    # or else there will be trouble when the skip verification happens
    # (in __init__.py, function player_worker)
    app.mpv.command('seek', time, 'absolute', None)
    return "ok"
