#!/bin/bash

sudo apt-get install python-tk python-pil.imagetk
sudo apt-get install libzbar0
sudo WIFI_INSTALL_CLI=False pip install wifi
sudo pip install -r requirements.txt
