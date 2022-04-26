import sqlite3


class User:
    """
    Une classe représentant un utilisateur. Possède les mêmes attributs que dans la base de donnée, dans ta table users.
    """

    def __init__(self, ident: int, username: str, password: str):
        """
        :param ident: ID de l'utilisateur dans la BDD.
        :param username: Nom d'utilisateur.
        :param password: sha512 hash du mot de passe.
        """
        self.ident = ident
        self.username = username
        self.password = password

    def __str__(self):
        """
        :returns: `self.username`
        """
        return self.username

    @classmethod
    def init_from_username(cls, database: str, username: str):
        """
        Renvoie un :class:`User` s'il existe déjà dans la base de donnée.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :param username: Nom d'utilisateur.
        :return: None si l'utilisateur n'a pas été trouvée, l'utilisateur sinon.
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("""SELECT id, user, pass FROM users WHERE user=?""",
                  (username,
                   ))
        r = c.fetchone()
        if r is None:
            return None
        assert r[1] == username
        return User(r[0], username, r[2])

    def insert_to_database(self, database: str):
        """
        Insére l'utilisateur dans la BDD.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        """
        # TODO: Checker que l'utilisateur n'existe pas déjà.
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute(
            """INSERT INTO users ("user", "pass") VALUES (?,?)""",
            (self.username,
             self.password))
        conn.commit()

    @classmethod
    def getUserCounts(cls, database: str, nbr: int, date=0, track: str = None):
        """
        Renvoie une liste des :class:`User` de taille `nbr`.
        La liste est triée par nombre de musiques ajoutées (ie nombre de logs).
        Il est possible de restreindre à une période temporelle avec l'argument `date`.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :param nbr: Taille maximale de la liste en sortie.
        :param date: Date, permet de faire des stats journalières et hebdomadaires.
        :returns: Liste de (Username, Nombre de musiques ajoutées).
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        if track:
            c.execute("""
                SELECT user, count(user)\
                FROM  users, log, track_info\
                WHERE log.userid = users.id\
                    AND log.trackid = track_info.id\
                    AND log.time > ?\
                    AND track_info.track = ? \
                GROUP BY user \
                ORDER BY count(user) DESC\
                """,
                      (date, track,))
        else:
            c.execute("""
                SELECT user, count(user)\
                FROM  users, log\
                WHERE log.userid = users.id\
                    AND log.time > ?\
                GROUP BY user \
                ORDER BY count(user) DESC\
                """,
                      (date,))
        r = c.fetchall()
        if r is None:
            return None
        if nbr < 0:
            return r
        else:
            return r[:nbr]

    @classmethod
    def getTheme(cls, database, user: str):
        """
        Renvoie le thème de l'utilisateur, s'il existe.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :param user: Nom d'utilisateur.
        :returns: Nom du thème, ou None.
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("SELECT theme from users where user=?", (user,))
        r = c.fetchall()
        if r is None:
            return None
        if len(r) > 0:
            return r[0][0]
        return None

    @classmethod
    def setTheme(cls, database, user: str, theme: str):
        """
        Set le thème de l'utilisateur, s'il existe.

        :param database: Path vers la base de donnée. Généralement app.config["DATABASE_PATH"].
        :param user: Nom d'utilisateur.
        """
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute("UPDATE users SET theme=? where user=?", (theme, user))
        conn.commit()
