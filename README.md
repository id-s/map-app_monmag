# map-app_monmag

## 開発環境構築

バージョン、パッケージの違いによる動く/動かないといった問題を避けるため、以下の手順で開発環境を構築することを勧めます。

[前提]
* pyenv, virtualenvがインストールされていること

★Macの場合(Windowsでも同様の手順が必要かもしれません。未確認)

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

★Windowsの場合
python+pip+virtualenvで構築できます。※他の方法もあるかもしれません。

手順

①pythonのインストール

②環境変数の確認、設定
 コマンドプロンプトorPowerShellで以下のコマンドを実行
 Ver情報が出力たら、環境変数の設定OK
 ```
 $ python -V
　Python 2.7.9
 ```
③pipでvirtualenvをインストール
 ```
 $ pip install virtualenv
 ```
④gitからmap-app_monmagをダウンロード(またはclone)

⑤map-app_monmagディレクトリに移動

⑥仮想環境の構築
 ```
 $ virtualenv -p python.exeのフルパス env
 ```
⑦仮想環境の切り替え
 ```
 $ .\env\Scripts\activate
(env) $ pip install -r requirements.txt
(env) $ pip install opencv-python
 ```
⑧map.pyの微修正
 ```
 ・locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')
 でエラーがでる場合コメントアウト
 ・mqtt.xmlを持っていない場合 APP_MODEを"normal"=>"test"に変更
 APP_MODE = os.getenv("APP_MODE", "test")
 ・APP_ENVを"Monmag"=>"Win"に変更
 APP_ENV = os.getenv("APP_ENV", "Win")
 ```
⑨map.py実行
 ```
 python map.py
 ```

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

