from flask import Blueprint, render_template, redirect, session, request, flash
from flask import current_app as app
import sqlite3
from passlib.hash import pbkdf2_sha256

from jukebox.src.User import User
from jukebox.src.util import *
auth = Blueprint('auth', __name__)


@auth.route("/auth", methods=['GET', 'POST'])
def auth_page():
    conn = sqlite3.connect(app.config["DATABASE_PATH"])
    c = conn.cursor()

    if request.method == 'GET':
        # If the user is already logged in, redirect them to the app
        if "user" in session and session['user'] is not None:
            return redirect("/app")
        else:  # else, render login form
            return render_template("auth.html")

    # handle account creation
    success = False
    if request.form["action"] == "new":
        # we must first check if the username isn't aleady taken
        # then we do as usual
        # if it is, display a notification
        user = User.init_from_username(
            app.config["DATABASE_PATH"],
            request.form["user"]
        )
        if user is not None:
            flash("Account already exists")
            return render_template("auth.html")
        password_hashed = pbkdf2_sha256.hash(request.form["pass"])
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
            if (user is not None
                    and pbkdf2_sha256.verify(
                        request.form["pass"],
                        user.password)):
                app.logger.info("Logging in {}".format(request.form["user"]))
                if not request.form['user'] in app.user_add_limits.keys():
                    app.user_add_limits[request.form['user']] = 50
                    app.user_rem_limits[request.form['user']] = 1
                    if request.form['user'] in app.premiums:
                        app.user_rem_limits[request.form['user']] = 50
                        app.user_add_limites[request.form['user']] = 1000000

                session['user'] = request.form['user']
                return redirect("/app")
        except ValueError:
            pass
        flash("Raté")
        app.logger.info("Failed log attempt for %s", request.form["user"])
    # if account successfully created OR login successful
    return render_template("auth.html")


@auth.route("/logout", methods=['GET', 'POST'])
@requires_auth
def logout():
    if request.method == "POST":
        session['user'] = None
        return redirect("/auth")
    else:
        return render_template("logout.html", user=session["user"])
