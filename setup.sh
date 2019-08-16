#!/bin/bash

# setting
log_file=./logs/setup.log

ngrok_download_file=ngrok-stable-linux-arm.zip
ngrok_download_url=https://bin.equinox.io/c/4VmDzA7iaHb/$ngrok_download_file


# locale
sudo sed -i -e 's/^# ja_JP.UTF-8/ja_JP.UTF-8/' /etc/locale.gen
sudo locale-gen


# install
sudo apt-get install -y python-tk python-pil.imagetk 1>> $log_file 2>&1
sudo apt-get install -y libzbar0 1>> $log_file 2>&1
sudo WIFI_INSTALL_CLI=False pip install wifi 1>> $log_file 2>&1
sudo pip install -r requirements.txt 1>> $log_file 2>&1

sudo systemctl enable vncserver-x11-serviced.service

if [ -z "`ngrok version | grep version`" ]; then
  wget $ngrok_download_url 1>> $log_file 2>&1
  sudo unzip $ngrok_download_file -d /usr/local/bin 1>> $log_file 2>&1
  ngrok version 1>> $log_file 2>&1
fi


# module
sudo modprobe bcm2835-v4l2
if [ -z `grep bcm2835-v4l2 /etc/modules` ]; then
  echo | sudo tee -a /etc/modules
  echo "# MAP" | sudo tee -a /etc/modules
  echo "bcm2835-v4l2" | sudo tee -a /etc/modules
fi

