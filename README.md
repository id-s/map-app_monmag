# map-app_monmag

## 開発環境構築

バージョン、パッケージの違いによる動く/動かないといった問題を避けるため、以下の手順で開発環境を構築することを勧めます。

[前提]
* pyenv, virtualenvがインストールされていること

Macの場合(Windowsでも同様の手順が必要かもしれません。未確認)

```
$ brew install zbar
```

```
$ cd map-app_monmag
$ pyenv install 2.7.9
$ virtualenv -p ~/.pyenv/versions/2.7.9/bin/python2.7 env
$ source env/bin/activate
(env) $ pip install -r requirements.txt
(env) $ pip install opencv-python
```

opencvをrequirements.txtに入れていないのは、Monmag側ではすでに(?)入っていたため。

現在、Monmagで使われているフォントは"Droid Sans Japanese"。
これが開発PCにインストールされていない場合は以下よりダウンロードしてインストールしてください。
https://github.com/jenskutilek/free-fonts/blob/master/Droid/Droid%20Sans%20Japanese/DroidSansJapanese.ttf

アプリの起動は下記コマンドにて(APP_ENVの値は"Monmag"以外なら何でもOK)。

```
(env) $ APP_ENV=Mac python map.py
```

上記以外に以下のオプションが利用可能

ON_DEBUG: "True"とすると、デバッグレベルのログが出力される
APP_MODE: "test"とすると、テストモードで起動する(設定より切り替え可能)


## 実行環境構築

Monmagのターミナルにて以下を実行する。

```
$ sudo apt-get install git
$ mkdir Git
$ cd Git
$ git clone https://github.com/id-s/map-app_monmag.git
$ cd map-app_monmag
$ chmod a+x *.sh
$ ./setup.sh
```

さらに`sudo raspi-config`から、ロケール(ja_JP.UTF-8)を追加する。
4 Localisation Options > I1 Change Locale > Ok > "ja_JP.UTF-8 UTF-8"まで移動し、スペースを押す > エンターを押す > Ok > None > Finish

Wi-Fi設定を可能にするため、アプリの起動は`sudo python map.py`で行う必要がある。

### 自動起動設定

ID-Syncの自動起動を無効化する。

```
pi@raspberrypi:~/Git/map-app_monmag $ sudo vi /etc/init.d/monmag-startup.sh

#!/bin/sh
...
### END INIT INFO

exit 0 # TEST <<< 追加

update_dir="/home/pi/Git/monmag-rpi-bin/"
bin_dir="/home/pi/Git/monmag-rpi-bin/ui/"
...

pi@raspberrypi:~/Git/map-app_monmag $  vi ~/.config/lxsession/LXDE-pi/autostart

...
#@sh /home/pi/qrcode_startup.sh
@sh /home/pi/Git/map-app_monmag/startup.sh
```

