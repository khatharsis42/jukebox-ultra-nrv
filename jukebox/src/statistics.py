import datetime
from typing import List

from flask_table import Table, Col, LinkCol

from jukebox.src.User import User
from jukebox.src.Track import Track


class StatsUsersTable(Table):
    name = LinkCol(name='User',
                   attr='name',
                   endpoint='main.user_stats',
                   url_kwargs=(dict(username="name")))
    description = Col('Count')


class StatsTracksTable(Table):
    name = LinkCol(name='Track',
                   attr='name',
                   endpoint='main.track_stats',
                   url_kwargs=(dict(track='id')))
    description = Col('Count')


class StatsUsersItem(object):
    def __init__(self, user, count):
        self.name = user
        self.description = count


class StatsTracksItem(object):
    def __init__(self, name, count, id = None):
        self.name = name
        self.description = count
        self.id = id
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
