import sqlite3
con = sqlite3.connect("jukebox.sqlite3")
c = con.cursor()
c.execute("""
ALTER TABLE users \
ADD theme VARCHAR(255);
""")
con.commit()
