# Enable debug flask server
DEBUG=True
# Listen address. Set to 0.0.0.0 for all interfaces
LISTEN_ADDR="0.0.0.0"
# Listen port
LISTEN_PORT=8080
# Channel used for volume control (see output of amixer)
AMIXER_CHANNEL="Master"
# Flask secret encryption key. Do not leave blank
SECRET_KEY=""
# Path to your sqlite database. Will be created on first run
DATABASE_PATH = "jukebox.sqlite3"
# Path to where your tracks will be temporary donwloaded, if needed
TEMP_DOWNLOAD_PATH = "jukebox/src/backends/temp_downloads/"
# Your YouTube API Key. Needed for YouTube searches
# This is a list so that we can use multiples keys,
# and switch once one of these is entirely used.
YOUTUBE_KEY=[""]
# Enabled search backends
SEARCH_BACKENDS = [
  "youtube",
  "bandcamp",
  "soundcloud",
  "jamendo",
  "generic",
  "twitch",
  "direct_files"
]
# Name of the app
JK_NAME="Jukebox Ultra NRV MkV"
