# map-app_monmag

## 開発環境構築

バージョン、パッケージの違いによる動く/動かないといった問題を避けるため、以下の手順で開発環境を構築することを勧めます。

[前提]
* pyenv, virtualenvがインストールされていること

```
$ cd map-app_monmag
$ pyenv install 3.4.2
$ virtualenv -p ~/.pyenv/versions/3.4.2/bin/python3.4 env
$ source env/bin/activate
$ pip install -r requirements.txt
```

現在、Monmagで使われているフォントは"Droid Sans Japanese"。
これが開発PCにインストールされていない場合は以下よりダウンロードしてインストールしてください。
https://github.com/jenskutilek/free-fonts/blob/master/Droid/Droid%20Sans%20Japanese/DroidSansJapanese.ttf


## 実行環境構築

Monmagのターミナルにて以下を実行する。

```
$ sudo apt-get install python3-tk
$ sudo apt-get install python3-pil.imagetk
$ cd ~/Git
$ git clone https://github.com/id-s/map-app_monmag.git
$ cd map-app_monmag
$ pip3 install -r requirements.txt
```

