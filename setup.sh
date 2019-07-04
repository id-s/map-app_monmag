#!/bin/bash

# setting
log_file=./logs/setup.log

ngrok_download_file=ngrok-stable-linux-arm.zip
ngrok_download_url=https://bin.equinox.io/c/4VmDzA7iaHb/$ngrok_download_file


# locale
sudo locale-gen ja_JP.UTF-8


# install
sudo apt-get install -y python-tk python-pil.imagetk >> $log_file
sudo apt-get install -y libzbar0 >> $log_file
sudo WIFI_INSTALL_CLI=False pip install wifi >> $log_file
sudo pip install -r requirements.txt >> $log_file

wget $ngrok_download_url >> $log_file
sudo unzip $ngrok_download_file -d /usr/local/bin >> $log_file
ngrok version >> $log_file


# module
sudo modprobe bcm2835-v4l2
if [ -z `grep bcm2835-v4l2 /etc/modules` ]; then
  echo | sudo tee -a /etc/modules
  echo "# MAP" | sudo tee -a /etc/modules
  echo "bcm2835-v4l2" | sudo tee -a /etc/modules
fi

