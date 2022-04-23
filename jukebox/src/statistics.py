from flask_table import Table, Col, LinkCol

from jukebox.src.User import User
from jukebox.src.Track import Track
from flask_table import Table, Col, LinkCol

from jukebox.src.Track import Track
from jukebox.src.User import User


# J'ai franchement la flemme de faire la documentation de ce fichier...
class StatsUsersTable(Table):
    name = LinkCol(name='User',
                   attr='name',
                   endpoint='main.user_stats',
                   url_kwargs=(dict(username="name")))
    description = Col('Count')


class StatsUsersItem(object):
    def __init__(self, user, count):
        self.name = user
        self.description = count


class StatsTracksTable(Table):
    name = LinkCol(name='Track',
                   attr='name',
                   endpoint='main.track_stats',
                   url_kwargs=(dict(track='id')))
    description = Col('Count')


class StatsTracksItem(object):
    def __init__(self, name, count, id=None):
        self.name = name
        self.description = count
        self.id = id
        # NB: Cet id est choisi purement au hasard dans le cas de
        # plusieurs musiques ayant le même nom


class HistoryTracksTable(Table):
    name = LinkCol(name='Track',
                   attr='name',
                   endpoint='main.track_stats',
                   url_kwargs=(dict(track='id')))
    description = Col('Count')


class HistoryTracksItem(object):
    def __init__(self, name, id, user):
        self.name = name
        self.id = id
        self.description = user
        # NB: Cet id est choisi purement au hasard dans le cas de
        # plusieurs musiques ayant le même nom


def create_html_users(database, date=0, nbr=10, track=False):
    items = []
    usercounts = User.getUserCounts(database, nbr, date=date, track=track)
    for couple in usercounts:
        # we get user, count
        user = couple[0]
        count = couple[1]
        items.append(StatsUsersItem(user=user, count=count))

    return StatsUsersTable(items).__html__()


def create_html_tracks(database, date=0, nbr=10, user=False):
    items = []
    trackcounts = Track.getTrackCounts(database, nbr, date=date, user=user)
    for couple in trackcounts:
        # we get user, count
        track = couple[0]
        count = couple[1]
        id = couple[2]
        items.append(StatsTracksItem(name=track, count=count, id=id))
    return StatsTracksTable(items).__html__()


def create_history_tracks(database, nbr: int = 50):
    items = []
    trackcounts = Track.get_history(database, nbr)
    for trouple in trackcounts:
        track, track_id, user = trouple
        items.append(HistoryTracksItem(name=track, id=track_id, user=user))
    return StatsTracksTable(items).__html__()
