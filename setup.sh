#!/bin/bash

sudo apt-get install python-tk python-pil.imagetk >> ./logs/setup.log
sudo apt-get install libzbar0 >> ./logs/setup.log
sudo WIFI_INSTALL_CLI=False pip install wifi >> ./logs/setup.log
sudo pip install -r requirements.txt >> ./logs/setup.log
