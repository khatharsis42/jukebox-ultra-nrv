import mpv
import jukebox.src.lib.idle as idle
import requests
import sys
import threading
import time
import subprocess
# I have no idea what this is used for
# I have not read it, not even once, and I'm not sure it's ever called
# So what the heck
# - Khâtharsis

class MyMPV(mpv.MPV):
    def __init__(self, argv):
        super().__init__(argv, window_id=None, debug=False)
        self.loaded = threading.Event()
    def on_property_time_pos(self, position=None):
        pass

    def load(self, path):
        self.loaded.clear()
        self.command("loadfile", path, "replace")
        self.set_property("playlist-pos", 0)

    def on_file_loaded(self):
        self.loaded.set()

    def pos(self):
        return self.get_property("time-pos")
    def file(self):
        try:
            return self.get_property("path")
        except mpv.MPVCommandError:
            return None

    def finished(self):
        r = None
        try:
            r=self.get_property("eof-reached")
            return r
        except (mpv.MPVCommandError, BrokenPipeError):
            return True

    def play(self):
        self.set_property("pause", False)

    def pause(self):
        self.set_property("pause", True)

    def seek(self, position):
        self.command("seek", position, "absolute")

if __name__ == "__main__":
    url = "http://" + sys.argv[1] + "/sync"
    timeout = int(sys.argv[2])
    player = None
    while True:
        try:
            sync_data = requests.get(url).json()
        except:
            print("connexion error, retrying...")
            time.sleep(2)
        if idle.getIdleSec() < timeout or len(sync_data["playlist"]) == 0:
            if player:
                print("User detected or playlist empty, switching to mame")
                player.close()
                try:
                    subprocess.run(["killall", "-s", "SIGCONT", "mame"])
                    subprocess.run(["wmctrl", "-a", "mame"])
                except: pass
                player = None
            time.sleep(1)
            continue
        if not player:
            print("Idle for more than {}, switching to mpv".format(timeout))
            try:
                subprocess.run(["killall", "-s", "SIGSTOP", "mame"])
            except:
                pass
            player = MyMPV(["--no-input-default-bindings", "--no-audio", "--no-stop-screensaver", "--ontop", "--no-border", "--geometry=100%x100%+0+0"])
        orig_t = time.time()

        if player.file() != sync_data["playlist"][0]["url"]:
            print("loading new track {} {}".format(player.file(),sync_data["playlist"][0]["url"]))
            player.load(sync_data["playlist"][0]["url"])
            player.pause()
            player.loaded.wait()
            print("loaded")
        else:
            local = player.pos()
            remote = sync_data["time"]
            delay = time.time()-orig_t
            delta = remote - local
            offset = 0.5
            print("local: {} | remote : {} | delta {} | delay {}".format(local, remote, delta, delay))
            if abs(delta) >= offset: # catch up
                print("catching up")
                player.seek(remote + delay + offset/2) # go ahead
            elif delta > 0.001: # sync
                print("en avance de {}".format(delta))
                player.pause()
                time.sleep(abs(delta+delay)/2)
                player.play()

            player.play()
        time.sleep(1)
    mpv.close()
