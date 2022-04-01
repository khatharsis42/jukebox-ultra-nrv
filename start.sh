# /bin/bash
screen -XS Jukebox quit;
screen -d -S Jukebox -m python3 run.py;
echo "Jukebox" $(cat version.txt) "launched !";
