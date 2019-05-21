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
```


## 実行環境構築

Monmagのターミナルにて以下を実行する。

```
$ sudo apt-get install python3-tk
$ cd ~/Git
$ git clone https://github.com/id-s/map-app_monmag.git
```
