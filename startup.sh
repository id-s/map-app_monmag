#!/bin/bash

# setting
ymd=`date +"%Y%m%d"`
log_file=logs/app_$ymd.log

ngrok_authtoken=6cmuFXybMEhdbwYV7e5i1_5yZA1EDSTLfxGqTUTphdj


cd ~/Git/map-app_monmag


# update
git pull >> $log_file
sudo pip install -r requirements.txt >> $log_file


# ngrok
sudo ngrok authtoken $ngrok_authtoken >> $log_file


sudo python map.py >> $log_file

