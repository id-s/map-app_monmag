#!/bin/bash

ymd=`date +"%Y%m%d"`

# update
git pull >> ~/logs/app_$ymd.log
sudo pip install -r requirements.txt >> ~/logs/app_$ymd.log

sudo python map.py >> ~/logs/app_$ymd.log
