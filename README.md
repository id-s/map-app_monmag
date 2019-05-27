# map-app_monmag

## 開発環境構築

バージョン、パッケージの違いによる動く/動かないといった問題を避けるため、以下の手順で開発環境を構築することを勧めます。

[前提]
* pyenv, virtualenvがインストールされていること

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
$ sudo apt-get install python-tk
$ sudo apt-get install python-pil.imagetk
$ cd ~/Git
$ git clone https://github.com/id-s/map-app_monmag.git
$ cd map-app_monmag
$ sudo pip install -r requirements.txt
```

