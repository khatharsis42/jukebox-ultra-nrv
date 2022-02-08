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
                   url_kwargs=(dict(track="name")))
    description = Col('Count')


class StatsUsersItem(object):
    def __init__(self, user, count):
        self.name = user
        self.description = count


class StatsTracksItem(object):
    def __init__(self, name, count):
        self.name = name
        self.description = count


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
        items.append(StatsTracksItem(name=track, count=count))
    return StatsTracksTable(items).__html__()
