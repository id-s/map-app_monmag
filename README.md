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


## 実行環境構築

Monmagのターミナルにて以下を実行する。

```
$ sudo apt-get install python-tk python-pil.imagetk
$ sudo apt-get install libzbar0
$ cd ~/Git
$ git clone https://github.com/id-s/map-app_monmag.git
$ cd map-app_monmag
$ sudo pip install -r requirements.txt
```

さらに`sudo raspi-config`から、ロケール(ja_JP.UTF-8)を追加する。
4 Localisation Options > I1 Change Locale > Ok > "ja_JP.UTF-8 UTF-8"まで移動し、スペースを押す > エンターを押す > Ok > None > Finish
