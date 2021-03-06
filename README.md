# map-app_monmag

## 開発環境構築

バージョン、パッケージの違いによる動く/動かないといった問題を避けるため、以下の手順で開発環境を構築することを勧めます。

[前提]

* pyenv, virtualenvがインストールされていること

Macの場合

```
$ brew install zbar
```

```
$ cd map-app_monmag
$ pyenv install 2.7.9
```

Windowsの場合

Windowsではpyenvが使えませんので、Python2.7.9を直接インストールしてください


[共通手順]

```
$ virtualenv -p ~/.pyenv/versions/2.7.9/bin/python2.7 env
$ source env/bin/activate
(env) $ pip install -r requirements.txt
(env) $ pip install opencv-python
```

`virtualenv -p`の後ろには、それぞれの環境におけるpython2.7へのパスを指定する。
opencvをrequirements.txtに入れていないのは、Monmag側ではすでに(ID-Sync用として)入っていたため。

現在、Monmagで使われているフォントは"Droid Sans Japanese"。
これが開発PCにインストールされていない場合は以下よりダウンロードしてインストールしてください。
https://github.com/jenskutilek/free-fonts/blob/master/Droid/Droid%20Sans%20Japanese/DroidSansJapanese.ttf


アプリの起動は下記コマンドにて。
>APP_ENVの値は実行環境によって異なります。
>Macの場合 APP_ENV=Mac
>Windowsの場合 APP_ENV=Win

```
(env) $ APP_ENV=Mac APP_MODE=test python map.py
```

上記以外に以下のオプションが利用可能

ON_DEBUG: "True"とすると、デバッグレベルのログが出力される


## 実行環境構築

Monmagにssh接続し、以下を実行する。

```
$ cd Git
$ git clone https://github.com/id-s/map-app_monmag.git
$ cd map-app_monmag
$ chmod a+x *.sh
$ ./setup.sh
```

Wi-Fi設定を可能にするため、アプリの起動は`sudo python map.py`で行う必要がある。

