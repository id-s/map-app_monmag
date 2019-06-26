#!/bin/bash

sudo apt-get install -y python-tk python-pil.imagetk >> ./logs/setup.log
sudo apt-get install -y libzbar0 >> ./logs/setup.log
sudo WIFI_INSTALL_CLI=False pip install wifi >> ./logs/setup.log
sudo pip install -r requirements.txt >> ./logs/setup.log

sudo modprobe bcm2835-v4l2
if [ -z `grep bcm2835-v4l2 /etc/modules` ]; then
  echo | sudo tee -a /etc/modules
  echo "# MAP" | sudo tee -a /etc/modules
  echo "bcm2835-v4l2" | sudo tee -a /etc/modules
fi
