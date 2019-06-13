#!/bin/bash

cd ~/Git/map-app_monmag

ymd=`date +"%Y%m%d"`
log_file=logs/app_$ymd.log

# update
git pull >> $log_file
sudo pip install -r requirements.txt >> $log_file

sudo python map.py >> $log_file

