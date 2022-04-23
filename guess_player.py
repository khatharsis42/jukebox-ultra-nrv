import matplotlib.pyplot as plt
import sqlite3

from typing import List

NUMBER_OF_USER = 20
NUMBER_OF_TRACK = 100

con = sqlite3.connect("jukebox.sqlite3")
c = con.cursor()

c.execute("""
    SELECT user, count(user)
    FROM  users, log
    WHERE log.userid = users.id
    GROUP BY user 
    ORDER BY count(user) DESC
""")
r = c.fetchall()[:NUMBER_OF_USER]
top_users = [u[0] for u in r]
graphs = {}
names = {}
for user in top_users:
    c.execute(f"""
        SELECT track, count(track)
        FROM  track_info, log, users 
        WHERE log.trackid = track_info.id 
            and log.userid = users.id 
            and users.user = ?
        GROUP BY track_info.track order by count(trackid) DESC, log.id DESC
        """, (user,))
    temp = c.fetchall()
    graphs[user] = [x[1]/temp[0][1] for x in temp[:NUMBER_OF_TRACK]]
    names[user] = [x[0] for x in temp[:NUMBER_OF_TRACK]]

ranges = [
    {"from": ord(u"\u3300"), "to": ord(u"\u33ff")},  # compatibility ideographs
    {"from": ord(u"\ufe30"), "to": ord(u"\ufe4f")},  # compatibility ideographs
    {"from": ord(u"\uf900"), "to": ord(u"\ufaff")},  # compatibility ideographs
    {"from": ord(u"\U0002F800"), "to": ord(u"\U0002fa1f")},  # compatibility ideographs
    {'from': ord(u'\u3040'), 'to': ord(u'\u309f')},  # Japanese Hiragana
    {"from": ord(u"\u30a0"), "to": ord(u"\u30ff")},  # Japanese Katakana
    {"from": ord(u"\u2e80"), "to": ord(u"\u2eff")},  # cjk radicals supplement
    {"from": ord(u"\u4e00"), "to": ord(u"\u9fff")},
    {"from": ord(u"\u3400"), "to": ord(u"\u4dbf")},
    {"from": ord(u"\U00020000"), "to": ord(u"\U0002a6df")},
    {"from": ord(u"\U0002a700"), "to": ord(u"\U0002b73f")},
    {"from": ord(u"\U0002b740"), "to": ord(u"\U0002b81f")},
    {"from": ord(u"\U0002b820"), "to": ord(u"\U0002ceaf")}  # included as of Unicode 8.0
]


def is_cjk(char):
    return any([range["from"] <= ord(char) <= range["to"] for range in ranges])


def select_word(word: str, user: str):
    non_word = ([], [])
    contain_word = [[], []]
    for i in range(NUMBER_OF_TRACK):
        if word in names[user][i].lower():
            contain_word[0].append(i)
            contain_word[1].append(graphs[user][i])
        else:
            non_word[0].append(i)
            non_word[1].append(graphs[user][i])
    plt.bar(non_word[0], non_word[1], color="red", label=f"Ne contient pas {word}")
    plt.bar(contain_word[0], contain_word[1], color="green", label=f"Contient {word}")
    plt.ylabel("Nombre de fois où cette musique a été mise")
    plt.xlabel("Classement de la musique")
    plt.legend(loc="upper right")
    plt.show()


def select_japanese(user: str):
    non_word = ([], [])
    contain_word = [[], []]
    for i in range(NUMBER_OF_TRACK):
        if any(is_cjk(c) for c in names[user][i])\
                or "opening" in names[user][i].lower()\
                or "ending" in names[user][i].lower()\
                or "op" in names[user][i].lower()\
                or "ed" in names[user][i].lower():
            contain_word[0].append(i)
            contain_word[1].append(graphs[user][i])
        else:
            non_word[0].append(i)
            non_word[1].append(graphs[user][i])
    plt.bar(non_word[0], non_word[1], color="red", label="Musique Normale")
    plt.bar(contain_word[0], contain_word[1], color="green", label="Musique de Weeb")
    plt.ylabel("Nombre de fois où cette musique a été mise (relatif)")
    plt.xlabel("Classement de la musique")
    plt.legend(loc="upper right")
    plt.show()


select_word("evangelion", "Khatharsis")
select_word("evangelion", "yacine")


for user in top_users:
    print(f"User : {user} -> {names[user][:3]}")
    select_japanese(user)
    # plt.bar(range(NUMBER_OF_TRACK), [g / graphs[user][0] for g in graphs[user]])
    # plt.show()
