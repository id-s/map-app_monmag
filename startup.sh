#!/bin/bash

# update
git pull
sudo pip install -r requirements.txt

sudo python map.py
