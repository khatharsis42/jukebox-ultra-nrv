import random
import re
import datetime
import sys

import flask
from flask import Blueprint, render_template, redirect, session, jsonify, request, flash
from flask import current_app as app
from flask_wtf import FlaskForm
from typing import List
from wtforms import SelectField, SubmitField
from os import listdir
from os.path import isfile, join

from jukebox.src import playlist
from jukebox.src.util import *
from jukebox.src.Track import Track
from jukebox.src.statistics import create_html_users, create_html_tracks, create_history_tracks
from jukebox.src.backends.search import bandcamp, generic, jamendo, soundcloud, twitch, youtube
# import * ne fonctionne pas, wtf, une histoire de cache d'après Boisdal ?

main = Blueprint('main', __name__)


def get_style():
    cookie = request.cookies.get('style')
    if cookie is not None:
        return cookie
    try:
        if session["stylesheet"] is not None:
            stylesheet = session["stylesheet"]
        else:
            stylesheet = app.stylesheet
    except KeyError:
        stylesheet = app.stylesheet
    return stylesheet


def get_nav_links():
    if "NAV_LINKS" in app.config:
        return app.config["NAV_LINKS"]
    else:
        return []


@main.route("/app")
@requires_auth
def app_view():
    # app.logger.info("App access from %s", session["user"])
    return render_template("accueil.html",
                           user=session["user"], jk_name=app.config["JK_NAME"],
                           stylesheet=get_style(), navlinks=get_nav_links())


@main.route("/")
def accueil():
    return redirect("/app")


@main.route("/help")
def help():
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
    # we should add a modules argument to render_template to
    # display which search functions are available

    style_path = "jukebox/static/styles/custom/"
    styles = [(f, f) for f in listdir(style_path) if isfile(
        join(style_path, f)) and f[-4:] == ".css"]
    app.logger.info(styles)

    class SettingsForm(FlaskForm):
        style = SelectField("Styles", choices=styles)
        submit = SubmitField("Send")

    form = SettingsForm()

    if request.method == 'POST':
        # if not(form.validate()):
        #    flash('All fields are required.')
        #    app.logger.info("All fields are required.")
        #    return render_template('settings.html',
        #            jk_name = app.config["JK_NAME"],form = form)
        # else:
        # app.logger.info(request.form)
        style = request.form["style"]
        session["stylesheet"] = style
        resp: flask.Response = flask.make_response(
            render_template('settings.html', user=session["user"],
                            jk_name=app.config["JK_NAME"], form=form,
                            stylesheet=style, navlinks=get_nav_links()))
        resp.set_cookie('style', style)
        return resp
    elif request.method == 'GET':
        return render_template('settings.html', user=session["user"],
                               jk_name=app.config["JK_NAME"], form=form,
                               stylesheet=get_style(), navlinks=get_nav_links())


@main.route("/sync")
def sync():
    """
    Renvoie la playlist en cours
    """
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
    return render_template('user.html', user=session['user'],
                           jk_name=app.config["JK_NAME"],
                           user_name=username,
                           table_tracks_count_all=create_html_tracks(
                               app.config["DATABASE_PATH"], nbr=20, user=username),
                           table_tracks_count_week=create_html_tracks(
                               app.config["DATABASE_PATH"], nbr=10,
                               date=datetime.datetime.now() - datetime.timedelta(weeks=1),
                               user=username),
                           stylesheet=get_style(), navlinks=get_nav_links()
                           )


@main.route("/history/<number>", methods=['GET'])
@requires_auth
def history(number: int):
    number = int(number)
    # Je déteste python
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
    t: Track = Track.import_from_id(app.config["DATABASE_PATH"], track)
    if not t:
        #This means it's not a real id, but rather a youtube id
        #ie:
        t: Track = Track.import_from_url(app.config["DATABASE_PATH"], "https://www.youtube.com/watch?v="+track)
        if t:
            return redirect(f"/statistics/track/{t.ident}")
        # Then it's not https but http
        t: Track = Track.import_from_url(app.config["DATABASE_PATH"], "http://www.youtube.com/watch?v="+track)
        if t:
            return redirect(f"/statistics/track/{t.ident}")
        else:
            return redirect("/app")

    return render_template('track.html', user=session['user'],
                           jk_name=app.config["JK_NAME"],
                           track=t.track,
                           ident=t.ident,
                           table_users_count_all=create_html_users(
                               app.config["DATABASE_PATH"], nbr=20,
                               track=t.track),
                           stylesheet=get_style(), navlinks=get_nav_links()
                           )


@main.route("/status", methods=['GET'])
def status():
    # This is used in the portail.cj interface, to check if this is still up
    res = {
        "status": "UP"
    }
    return jsonify(res)


@main.route("/refresh-track", methods=['POST'])
@requires_auth
def refresh_track():
    """
    For now the interface isn't refreshed
    :return:
    """
    try:
        url = request.form["url"]
    except KeyError:
        return "nok"
    with app.database_lock:
        Track.refresh_by_url(app.config["DATABASE_PATH"], url)
    return "ok"


@main.route("/search", methods=['POST'])
@requires_auth
def search():
    """
    renvoie une liste de tracks correspondant à la requête depuis divers services
    :return: un tableau contenant les infos que l'on a trouvé
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
    regex_bandcamp = re.compile('^(http://|https://)?\S*\.bandcamp.com')
    regex_soundcloud = re.compile('^(http://|https://)?(www.)?soundcloud.com')
    regex_twitch = re.compile('^(http://|https://)?(www\.)?twitch.tv')
    regex_jamendo = re.compile('^(https?://)?(www.)?jamendo.com')
    regex_search_soundcloud = re.compile('(\!sc\s)|(.*\s\!sc\s)|(.*\s\!sc$)')
    regex_search_youtube = re.compile('(\!yt\s)|(.*\s\!yt\s)|(.*\s\!yt$)')
    regex_generic = re.compile(
        '(\!url\s)|(.*\s\!url\s)|(.*\s\!url$)|(\!g\s)|(.*\s\!g\s)|(.*\s\!g$)')

    # print("Query : \"" + query + "\"")
    # print("Regex match :", re.match(regex_generic, query))
    # print('jukebox.src.backends.search.jamendo' in sys.modules)
    # Bandcamp
    if re.match(regex_bandcamp, query) is not None \
            and 'jukebox.src.backends.search.bandcamp' in sys.modules:
        app.logger.info("Using Bancamp")
        for bandcamp in app.search_backends:
            if bandcamp.__name__ == 'jukebox.src.backends.search.bandcamp':
                break
        results += bandcamp.search_engine(query)
    # Soundcloud
    elif re.match(regex_soundcloud, query) is not None \
            and 'jukebox.src.backends.search.soundcloud' in sys.modules:
        app.logger.info("Using Soundcloud")
        for soundcloud in app.search_backends:
            if soundcloud.__name__ == 'jukebox.src.backends.search.soundcloud':
                break
        results += soundcloud.search_engine(query)
    elif re.match(regex_jamendo, query) is not None \
            and 'jukebox.src.backends.search.jamendo' in sys.modules:
        app.logger.info("Using Jamendo")
        for jamendo in app.search_backends:
            if jamendo.__name__ == 'jukebox.src.backends.search.jamendo':
                break
        results += jamendo.search_engine(query)
    # Soundcloud search
    elif re.match(regex_search_soundcloud, query) is not None \
            and 'jukebox.src.backends.search.soundcloud' in sys.modules:
        app.logger.info("Using Soundcloud search")
        for soundcloud in app.search_backends:
            if soundcloud.__name__ == 'jukebox.src.backends.search.soundcloud':
                break
        results += soundcloud.search_multiples(re.sub("\!sc", "", query))
    # Twitch
    elif re.match(regex_twitch, query) is not None \
            and 'jukebox.src.backends.search.twitch' in sys.modules:
        app.logger.info("Using Twitch")
        for twitch in app.search_backends:
            if twitch.__name__ == 'jukebox.src.backends.search.twitch':
                break
        results += twitch.search_engine(query)

    # Youtube search (explicit)
    elif re.match(regex_search_youtube, query) is not None \
            and 'jukebox.src.backends.search.youtube' in sys.modules:
        app.logger.info("Using YouTube search")
        for youtube in app.search_backends:
            if youtube.__name__ == 'jukebox.src.backends.search.youtube':
                break
        results += youtube.search_engine(re.sub("\!yt",
                                                "", query), use_youtube_dl=True)

    # Generic extractor
    elif re.match(regex_generic, query) is not None \
            and 'jukebox.src.backends.search.generic' in sys.modules:
        app.logger.info("Using Generic search")
        for generic in app.search_backends:
            if generic.__name__ == 'jukebox.src.backends.search.generic':
                break
        results += generic.search_engine(re.sub("\!url", "", query))

    elif 'jukebox.src.backends.search.youtube' in sys.modules:
        app.logger.info("Using Generic youtube search")
        for youtube in app.search_backends:
            if youtube.__name__ == 'jukebox.src.backends.search.youtube':
                break
        results += youtube.search_engine(query)
    else:
        app.logger.error("Error: no search module found")

    if len(app.search_cache) >= app.cache_size:
        app.search_cache.pop(random.choice(list(app.search_cache.keys())))
    app.search_cache[query] = results
    return jsonify(results)


@main.route('/pause_play', methods=['POST'])
def pause_test():
    app.mpv.command('cycle', 'pause', None)
    return "ok"


@main.route('/rewind', methods=['POST'])
def rewind():
    app.currently_played["duration"] += 10
    app.mpv.command('seek', - 10, 'relative', None)
    return "ok"


@main.route('/advance', methods=['POST'])
def advance():
    app.currently_played["duration"] -= 10
    app.mpv.command('seek', + 10, 'relative', None)
    return "ok"


@main.route('/jump', methods=['POST'])
def jump():
    timestamp = request.form["jump"]
    if (timestamp.count(':') == 0):
        time = int(timestamp)
    elif (timestamp.count(':') == 1):
        minutes, secondes = [int(t) for t in timestamp.split(":")]
        time = 60 * minutes + secondes
    elif (timestamp.count(':') == 2):
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
