#!/bin/bash

# setting
ymd=`date +"%Y%m%d"`
log_file=logs/app_$ymd.log

ngrok_authtoken=6cmuFXybMEhdbwYV7e5i1_5yZA1EDSTLfxGqTUTphdj


cd ~/Git/map-app_monmag
echo "\n[START UP] `date`" 1>> $log_file 2>&1


# update
git pull 1>> $log_file 2>&1
sudo pip install -r requirements.txt 1>> $log_file 2>&1


# ngrok
sudo ngrok authtoken $ngrok_authtoken 1>> $log_file 2>&1


sudo python map.py 1>> $log_file 2>&1

