# Jukebox Ultra NRV mkV
## New Repo
The current repo is now on GitLab. It's better this way apparently.
Here's the link: https://gitlab.com/club-jeux-int/jukebox-ultra-nrv

## Prerequisites

This application assumes it runs on Linux using Alsa.

Here's what you should have installed on your computer:
 - `python3`, obviously. This jukebox has been tested with Python3.7, 3.8 and 3.10.
 - pip requirements. Do do that, simply type `pip install -r requirements.txt`, and pip should do the rest. Note that you might have to use `pip3` insted of `pip`.
 - `alsa-utils`, grab it with the usual `sudo apt install alsa-utils`.
 - `libmpv-dev`, same thing, `sudo apt install libmpv-dev`.

### Youtube-dl

This application uses `yt-dlp` to grab some information about youtube videos, and `youtube-dl` to stream videos with mpv (this is the default behavior).

You can also make it so that it uses `yt-dlp` when streaming videos with mpv.
Bear in mind, YOU NEED LIBMPV-DEV >= 34.0 TO MAKE THIS WORK.
To do so, simply add your path to the `yt-dlp` binary (which you can find with `which yt-dlp`) do the config file.

## Installation

 - Clone the repo
 - Copy example_config.py.example to config.py and edit it 😎 (gitignore will make sure it is not gitted, cause you have a youtube api key in this)
 - To add a favicon, place it in the `jukebox/static` folder
 - Install requirements using `pip install -r requirements.txt`
 
 ```bash
 $ git clone https://github.com/matthias4217/jukebox-ultra-nrv.git
 $ cd jukebox-ultra-nrv
 $ pip install -r requirements.txt
 $ cp example_config.py config.py
 $ <edit config.py>
 $ <optionally add a favicon.ico>
 $ python3 run.py
 ```

## Usage

```bash
$ python3 run.py
```

or with a systemd service jukebox (currently very buggy)

```bash
$ systemctl start jukebox.service
```

Should you have screen, you can also use
```bash
$ ./start.sh
```
And if you have tmux, you can do
```bash
$ ./tmux.sh
```

## Security

The current use of this application is only among a "friendly" and local network.
As such, we haven't yet focused much on security.
The passwords are stored using pbkdf2_sha256 from library `passlib`.

## Troubleshooting

If you are using a systemctl service.
Check if the service is properly running :
 `$ sudo systemctl status jukebox`
 
Check the logs :
 `$ sudo journalctl -u jukebox.service`
 
Check if youtube-dl is working and up to date
 `youtube-dl https://www.youtube.com/watch?v=6xKWiCMKKJg`

If not, update it : `sudo youtube-dl -U`


## Outdated tracks

Tracks may be marked as obsolete.
These won't be displayed in the suggestions column.
Tracks become outdated if the source is youtube, and youtube-dl returns an "Error: Track not found.".
This means that the track doesn't exist on Youtube (it may have been removed, or is unavailable for any reason).
An obsolete track may become non-obsolete again if you refresh its metadata and Youtube doesn't return the previous
error.
To do this, you can simply search the track in the search engine.


## Development

For the logs, please use `app.logger.info`, `app.logger.warning` or `app.logger.error`.

## Licensing

This project uses Fontawesome icons, which underare Creative Commons Attribution 4.0
International license. The complete license can be found [here](https://fontawesome.com/license).

It also uses the [Sponsorblock MPV Script](https://github.com/po5/mpv_sponsorblock), albeit somewhat modified, so that it works as intented.
