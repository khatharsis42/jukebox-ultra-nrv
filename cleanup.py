# This file is here to clean the database
# Due to bad coding, some musics were added A LOT of times in the DB
import sqlite3
from datetime import datetime, timedelta
con = sqlite3.connect("jukebox.sqlite3")
cursor = con.cursor()


logsToRemove = []
cursor.execute('SELECT id, user from users')
userList = cursor.fetchall()
delta = timedelta(seconds=5)
format = '%Y-%m-%d %H:%M:%S'

for user in userList:
    print(f"User : {user[1]}")
    cursor.execute("""
    SELECT DISTINCT track_info.track
    FROM log, track_info
    WHERE log.trackid = track_info.id
        AND userid=?
    """, (user[0], ))
    liste = cursor.fetchall()
    for track in liste:
        #print(f"   Track : {track}")
        cursor.execute('SELECT id from track_info where track=?', track)
        idList = cursor.fetchall()
        if len(idList) == 1:
            cursor.execute('SELECT id, userid, time from log where trackid=? order by time asc',
                           idList[0])
        else:
            cursor.execute('SELECT id, userid, time from log where trackid=? or trackid=? order by time asc',
                           (idList[0][0], idList[1][0]))
        logList = cursor.fetchall()
        for i in range(0, len(logList)-1):
            now = logList[i]
            not_now = logList[i + 1]
            new_delta = datetime.strptime(not_now[2], format) - datetime.strptime(now[2], format)
            if new_delta < delta:
                print(f"   Removing log number {not_now[0]}, delta = {new_delta}, ({track[0]}), ")
                logsToRemove.append(not_now[0])
print(f"Removed {len(logsToRemove)} entries !")
for log in logsToRemove:
    cursor.execute("DELETE from log where id=?", (log,))
con.commit()
con.close()
