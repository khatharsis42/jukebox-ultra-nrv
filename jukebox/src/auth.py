from flask import Blueprint, render_template, redirect, session, request, flash
from flask import current_app as app
import sqlite3
from passlib.hash import pbkdf2_sha256

from jukebox.src.User import User
from jukebox.src.util import *

auth = Blueprint('auth', __name__)


@auth.route("/auth", methods=['GET', 'POST'])
def auth_page():
    """
    Fonction pour gérer l'authentification.

    GET -> Renvoie la page d'authentification ou d'acceuil selon si l'utilisateur est logged in ou pas.

    POST -> Permet de soit créer une nouvel utilisateur (action="new"), soit tenter une connection.
    """
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    c = conn.cursor()

    if request.method == 'GET':
        # If the user is already logged in, redirect them to the app
        if "user" in session and session['user'] is not None:
            return redirect("/app")
        else:  # else, render login form
            return render_template("auth.html")

    # handle account creation
    if request.form["action"] == "new":
        username, password = request.form["user"].strip(' '), request.form["pass"]
        if len(username) > 25:
            flash("Nom d'utilisateur trop long ! La limite est de 25 caractères.")
            return render_template("auth.html")
        if len(password) < 10:
            flash("Le mot de passe doit être de plus de 10 caractères.")
            return render_template("auth.html")
        user = User.init_from_username(
            app.config["DATABASE_PATH"],
            username
        )
        password_hashed = pbkdf2_sha256.hash(password)
        if user is not None:
            flash("Account already exists")
            return render_template("auth.html")
        user = User(None, request.form["user"], password_hashed)
        user.insert_to_database(app.config["DATABASE_PATH"])
        app.logger.info("Created account for %s", request.form["user"])
        session['user'] = request.form['user']
        return redirect("/app")

    else:  # handle login
        user = User.init_from_username(
            app.config["DATABASE_PATH"],
            request.form["user"]
        )
        try:
            if user is None:
                flash("Nom d'utilisateur invalide.")
            elif not pbkdf2_sha256.verify(request.form["pass"], user.password):
                flash("Mot de passe invalide.")
            else:
                app.logger.info("Logging in {}".format(request.form["user"]))
                session['user'] = request.form['user']
                return redirect("/app")
        except ValueError:
            pass
        app.logger.info("Failed log attempt for %s", request.form["user"])
    # if account successfully created OR login successful
    return render_template("auth.html")


@auth.route("/logout", methods=['GET', 'POST'])
@requires_auth
def logout():
    """
    GET -> Renvoie la page de confirmation de logout

    POST -> Logout.
    """
    if request.method == "POST":
        session['user'] = None
        return redirect("/auth")
    else:
        return render_template("logout.html", user=session["user"])
