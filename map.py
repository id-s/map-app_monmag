# -*- coding:utf-8 -*-

import Tkinter as tk
import tkFont as font
import tkMessageBox as messagebox

import cv2
import json
import locale
import os
import requests
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from PIL import Image, ImageTk
from pprint import pprint
from pyzbar.pyzbar import decode

APP_ENV = os.getenv("APP_ENV", "Monmag")
ON_DEBUG = os.getenv("ON_DEBUG", False)

locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')

WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320
PADDING = 4

PREVIEW_WIDTH = 320
PREVIEW_HEIGHT = 200
PREVIEW_OFFSET_X = PREVIEW_WIDTH / 2 + 64
PREVIEW_OFFSET_Y = PREVIEW_HEIGHT / 2 + 64

if APP_ENV == "Monmag":
    FONT_SIZE = 19
else:
    FONT_SIZE = 24

IMAGE_DIR = "images"
SOUND_DIR = "sounds"


class Menu(tk.Frame):
    """メニュー画面
    """

    def __init__(self, parent, controller):
        # FIXME: 画面の上下を反転させたいが指定不可？　他同様の画面あり
        tk.Frame.__init__(self, parent)
        self.controller = controller

        menu1 = tk.Button(self, text="MyShopクーポイントをスキャンする",
                          command=self.show_coupoint_scan)
        menu2 = tk.Button(self, text="流通会員カードをスキャンする",
                          command=lambda: controller.show_frame("CmdSelect"))

        menu1.pack()
        menu2.pack()


    def show_coupoint_scan(self):
        if self.check_coupoint():
            self.controller.frames["CoupointScan"].start_scan()
            self.controller.show_frame("CoupointScan")
        else:
            # FIXME: ダイアログの最大化ボタン他を消したいが、指定不可？　他同様
            messagebox.showerror("クーポイントエラー", "この店舗でご利用できるクーポイントはありません。")


    def check_coupoint(self):
        """クーポイント実施チェック
        """
        url = "https://qr-dot-my-shop-magee-stg.appspot.com/v1/check"
        headers = {"Content-Type": "application/json"}

        macaddress = context.get_macaddress()
        serialno = context.get_serialno()
        print("macaddress:{}, serialno:{}".format(macaddress, serialno)) ###
        data = {
            "terminal": {
                "macaddr": "48:a9:e9:dc:e2:65", #"00:00:00:00:00:00", # TODO:取得情報に差し替え
                "serial_no": "0123456789ABCDEF",
                }
            }

        print("POST {}".format(url))
        print(json.dumps(data))
        resp = requests.post(url, data=json.dumps(data), headers=headers)

        if resp.status_code == 200:
            print(resp.text)
            resp_data = resp.json()
            if resp_data["result"] == "success":
                return True
            else:
                return False
        else:
            print(resp.status_code)
            return False


class CoupointScan(tk.Frame):
    """クーポイントスキャン
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        label = tk.Label(self, text="クーポイントをスキャンしてください")
        label.pack(side="top", fill="x")

        self.preview = preview = tk.Canvas(self, width = PREVIEW_WIDTH, height = PREVIEW_HEIGHT, bg="blue")
        self.preview.pack(side="top")

        button = tk.Button(self, text="戻る",
                           command=self.back_menu)
        button.pack()

#         self.bind("<Activate>", self.start_scan) # Monmagではこのイベントが発生しない


    def start_scan(self, event = None):
        print("{}: start_scan".format(datetime.now()))
        self.on_scan = True
        self.capture = cv2.VideoCapture(0)
        self.after(100, self.update_preview)


    def update_preview(self):
        if not self.on_scan:
            return
        ret, frame = self.capture.read()
        if not ret:
            print("No capture")
            return

        print("{}: Update preview start".format(datetime.now()))
        self.image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if APP_ENV == "Monmag":
            self.image = self.image.transpose(1,0,2)[::-1] # -90度回転、詳細は https://qiita.com/matsu_mh/items/54b09273aef79ae027bc 参照
        self.decoded = decode(self.image) ###
        if self.decoded:
            for code in self.decoded:
                print(code)
                self.after_scan(code.data)
#                 self.preview.create_text(PREVIEW_OFFSET_X, PREVIEW_OFFSET_Y, text=code.data, tag="code") ###
                return

        self.image = Image.fromarray(self.image)
        self.image = ImageTk.PhotoImage(self.image)
#         print("w:{} x h:{}".format(self.image.width(), self.image.height())) ###
        self.preview.create_image(PREVIEW_OFFSET_X, PREVIEW_OFFSET_Y, image=self.image)
        print("{}: Update preview end".format(datetime.now()))
#         print("Update preview")

        self.after(100, self.update_preview)


    def after_scan(self, data):
        print("after_scan")
        coupoint_show = self.controller.frames["CoupointShow"]
        decoded_data = coupoint_show.parse_decoded_data(data)

        if decoded_data:
            if APP_ENV == "Monmag":
                sound_file = os.path.abspath(os.path.join(SOUND_DIR, "button.wav"))
                subprocess.call(["aplay", sound_file])
            coupoint = coupoint_show.get_coupoint(decoded_data)
            coupoint_show.show_coupoint(coupoint)
            self.on_scan = False
            self.capture.release()
            self.controller.show_frame("CoupointShow")
        else:
            messagebox.showerror("クーポイントエラー", "このQRコードはクーポイントではありません。")

            self.after(500, self.update_preview)


    def back_menu(self):
        print("back_menu")
        self.on_scan = False
        self.preview.delete("code")
        self.capture.release()
        self.controller.show_frame("Menu")


class CoupointShow(tk.Frame):
    """クーポイント詳細表示
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller


    def parse_decoded_data(self, decoded_data):
        """QRコードで読み取った文字列をパースする
        @see https://redmine.magee.co.jp/projects/myshop/wiki/%E3%82%AF%E3%83%BC%E3%83%9D%E3%82%A4%E3%83%B3%E3%83%88QR%E3%82%B3%E3%83%BC%E3%83%89%E3%81%AE%E4%BB%95%E6%A7%98
        """
        parsed_data = {}
        lines = decoded_data.split("\r\n")
        if (len(lines) == 4 and lines[0] == "MyShop"):
            parsed_data["customer_id"] = lines[1]
            parsed_data["carousel_id"] = lines[2]
        return parsed_data


    def get_coupoint(self, decoded_data):
        """クーポイントの詳細を取得する
        @param decoded_data QRコードから読み込まれたデータ(要parse)
        """
        url = "https://qr-dot-my-shop-magee-stg.appspot.com/v1/start"
        headers = {"Content-Type": "application/json"}

        macaddress = context.get_macaddress()
        serialno = context.get_serialno()
        print("macaddress:{}, serialno:{}".format(macaddress, serialno)) ###
        print("customer_id:{}, carousel_id:{}".format(decoded_data["customer_id"], decoded_data["carousel_id"])) ###
        data = {
            "terminal": {
                "macaddr": "48:a9:e9:dc:e2:65", #"00:00:00:00:00:00", # TODO:取得情報に差し替え
                "serial_no": "0123456789ABCDEF",
                },
            "carousel": {
                "customer_id": "20b097add4aea673e074d77fe1495434", # TODO:取得情報に差し替え
                "carousel_id": "327765a3ec00962ccc050e91354dcc64",
                }
            }

        print("POST {}".format(url))
        print(json.dumps(data))
        resp = requests.post(url, data=json.dumps(data), headers=headers)

        if resp.status_code == 200:
            print(resp.text)
            resp_data = resp.json()
            if resp_data["result"] == "regist":
                return resp_data["carousel"]
            else:
                print(resp_data["result"])
                return None
        else:
            print(resp.status_code)
            return None


    def show_coupoint(self, coupoint):
        self.title = tk.Label(self, text="来店ポイントプレゼント")
        self.title.pack(side="top", fill="x")

        self.use_term_label = tk.Label(self, text="利用可能期間", font=header_font, anchor="w")
        self.use_term_label.pack(side="top", fill="x")

        use_term_from = datetime.strptime(coupoint["use_term_from"], "%Y-%m-%d %H:%M:%S").strftime("%Y年%B%d日(%A)")
        use_term_to = datetime.strptime(coupoint["use_term_to"], "%Y-%m-%d %H:%M:%S").strftime("%Y年%B%d日(%A)")
        self.use_term = tk.Label(self, text="{} 〜 {}".format(use_term_from, use_term_to), font=body_font, justify="left")
        self.use_term.pack(side="top", fill="x")

        self.button = tk.Button(self, text="利用確定",
                                command=self.use_coupoint)
        self.button.pack(side="bottom", fill="x")


    def clear_coupoint(self):
        self.title.destroy()
        self.use_term_label.destroy()
        self.use_term.destroy()
        self.button.destroy()


    def use_coupoint(self):
        self.clear_coupoint()
        self.controller.show_frame("Menu")


class CmdSelect(tk.Frame):
    """流通ポイント処理選択
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        button1 = tk.Button(self, text="付与",
                            command=lambda: controller.show_frame("CardSelect"))
        button2 = tk.Button(self, text="取消",
                            command=lambda: controller.show_frame("Menu"))

        button1.pack()
        button2.pack()


class CardSelect(tk.Frame):
    """カード選択
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        clients = self.get_clients()
        if (clients):
            self.add_buttons(clients)


    def get_clients(self):
        """利用できるカードを取得する
        """
        url = "https://card-dot-my-shop-magee-stg.appspot.com/v1/check"
        headers = {"Content-Type": "application/json"}

        macaddress = context.get_macaddress()
        serialno = context.get_serialno()
        print("macaddress:{}, serialno:{}".format(macaddress, serialno)) ###
        data = {
            "terminal": {
                "macaddr": "48:a9:e9:dc:e2:65", #"00:00:00:00:00:00", # TODO:取得情報に差し替え
                "serial_no": "0123456789ABCDEF",
                }
            }

        print("POST {}".format(url))
        print(json.dumps(data))
        resp = requests.post(url, data=json.dumps(data), headers=headers)

        if resp.status_code == 200:
            print(resp.text)
            resp_data = resp.json()
            return resp_data["clients"]
        else:
            print(resp.status_code)
            return None


    def add_buttons(self, clients):
        for client in clients:
            resp = requests.get(client["img_url"], stream=True)
            if resp.status_code != 200:
                continue
            file_path = os.path.join(IMAGE_DIR, "{}.png".format(client["client_cd"]))
            with open(file_path, "wb") as f:
                f.write(resp.content)
                print("Download image: {}".format(file_path))

            image = Image.open(file_path)
            image = ImageTk.PhotoImage(image.resize((48, 48)))
            self.controller.client_images.append(image)
            button = tk.Button(self, compound="left", text=client["card_name"], image=image,
                               width=WINDOW_WIDTH - PADDING * 2,
                               command=self.select_card(client["client_cd"]))
            button.pack()


    def check_card(self):
        """カードのチェック
        @return "tel": 初回利用(次に電話番号入力画面を表示)
                "price": 二回目以降の利用(次に会計金額入力画面を表示)
                "failure": カード読み込み不正（選択された流通と読み込まれたカードが一致しない等）
                 None: サーバエラーなど
        """
        url = "https://card-dot-my-shop-magee-stg.appspot.com/v1/start"
        headers = {"Content-Type": "application/json"}

        macaddress = context.get_macaddress()
        serialno = context.get_serialno()
        print("macaddress:{}, serialno:{}".format(macaddress, serialno)) ###
        data = {
            "terminal": {
                "macaddr": "48:a9:e9:dc:e2:65", #"00:00:00:00:00:00", # TODO:取得情報に差し替え
                "serial_no": "0123456789ABCDEF",
                },
            "customer": {
                "card_no": "CRC0S0 32840000000000200001", # TODO:取得情報に差し替え
                "client_cd": context.selected_client,
                "card_id": 1,
                }
            }

        print("POST {}".format(url))
        print(json.dumps(data))
        resp = requests.post(url, data=json.dumps(data), headers=headers)

        if resp.status_code == 200 or resp.status_code == 404:
            print(resp.text)
            resp_data = resp.json()
            return resp_data["result"]
        else:
            print(resp.status_code)
            return None


    def select_card(self, client_cd):
        """カード選択時の処理
        http://memopy.hatenadiary.jp/entry/2017/06/11/220452 を参考に実装した。
        """
        def func():
            print("Select card:{}".format(client_cd))
            context.selected_client = client_cd
            result = self.check_card()
            if result == "tel":
                self.controller.show_frame("TelEntry")
            elif result == "price":
                self.controller.show_frame("SalesEntry")
            else:
                messagebox.showerror("エラー", "エラーが発生しました。")
        return func


class TelEntry(tk.Frame):
    """電話番号入力
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        caption = tk.Label(self, text="初めてのご利用の方は進呈ポイントをショートメールでお知らせします。",
                           wraplength=(WINDOW_WIDTH - PADDING * 2), justify="left", height=2, padx=PADDING)
        caption.pack(side="top", fill="x")

        label = tk.Label(self, text="電話番号入力")
        label.pack(side="top", fill="x")

        tel_entry = tk.Entry(self, textvariable=context.entry_text, font=default_font)
        tel_entry.pack(side="top", fill="x")

        button = tk.Button(self, text="確定",
                           command=self.show_sales_entry)
        button.pack(side="top")
        button.focus_set()

        tel_entry.bind("<FocusIn>", self.show_num_keys)


    def show_num_keys(self, event):
        context.entry_caption.set("電話番号入力")
        context.after_entry = "TelEntry"
        self.controller.show_frame("NumKeys")


    def show_sales_entry(self):
        context.entry_text.set("")
        self.controller.show_frame("SalesEntry")


class SalesEntry(tk.Frame):
    """会計金額入力
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        label = tk.Label(self, text="会計金額入力")
        label.pack(side="top", fill="x")

        sales_entry = tk.Entry(self, textvariable=context.entry_text, font=default_font)
        sales_entry.pack(side="top", fill="x")

        label2 = tk.Label(self, text="ポイント")
        label2.pack(side="top", fill="x")

        point_entry = tk.Entry(self, textvariable=context.point_num, font=default_font)
        point_entry.pack(side="top", fill="x")

        button = tk.Button(self, text="付与確定",
                           command=lambda: controller.frames["Finish"].show("流通ポイントを付与しました。"))
        button.pack(side="top")
        button.focus_set()

        sales_entry.bind("<FocusIn>", self.show_num_keys)


    def show_num_keys(self, event):
        context.entry_caption.set("会計金額入力")
        context.after_entry = "SalesEntry"
        self.controller.show_frame("NumKeys")


    def calc_point(self, sales):
        """付与ポイント算出
        """
        url = "https://card-dot-my-shop-magee-stg.appspot.com/v1/calc"
        headers = {"Content-Type": "application/json"}

        macaddress = context.get_macaddress()
        serialno = context.get_serialno()
        print("macaddress:{}, serialno:{}".format(macaddress, serialno)) ###
        data = {
            "terminal": {
                "macaddr": "48:a9:e9:dc:e2:65", #"00:00:00:00:00:00", # TODO:取得情報に差し替え
                "serial_no": "0123456789ABCDEF",
                },
            "customer": {
                "card_no": "CRC0S0 32840000000000200001", # TODO:取得情報に差し替え
                "price": sales,
                "client_cd": context.selected_client,
                "card_id": 1,
                }
            }

        print("POST {}".format(url))
        print(json.dumps(data))
        resp = requests.post(url, data=json.dumps(data), headers=headers)

        if resp.status_code == 200:
            print(resp.text)
            resp_data = resp.json()
            if resp_data["result"]:
                return resp_data["result"]
            else:
                return None
        else:
            print(resp.status_code)
            return None


class NumKeys(tk.Frame):
    """ソフトキーボード
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        caption = tk.Label(self, textvariable=context.entry_caption)
        caption.pack(side="top", fill="x")

        entry = tk.Entry(self, textvariable=context.entry_text, font=default_font)
        entry.pack(side="top", fill="x")

        numkeys = tk.Frame(self)
        numkeys.pack(side="top", fill="x")

        numkeys.columnconfigure(0, weight=1)
        numkeys.columnconfigure(1, weight=1)
        numkeys.columnconfigure(2, weight=1)

        button_7 = tk.Button(numkeys, text="7", command=lambda: self.add_num("7")).grid(column=0, row=0, sticky="nswe")
        button_8 = tk.Button(numkeys, text="8", command=lambda: self.add_num("8")).grid(column=1, row=0, sticky="nswe")
        button_9 = tk.Button(numkeys, text="9", command=lambda: self.add_num("9")).grid(column=2, row=0, sticky="nswe")

        button_4 = tk.Button(numkeys, text="4", command=lambda: self.add_num("4")).grid(column=0, row=1, sticky="nswe")
        button_5 = tk.Button(numkeys, text="5", command=lambda: self.add_num("5")).grid(column=1, row=1, sticky="nswe")
        button_6 = tk.Button(numkeys, text="6", command=lambda: self.add_num("6")).grid(column=2, row=1, sticky="nswe")

        button_1 = tk.Button(numkeys, text="1", command=lambda: self.add_num("1")).grid(column=0, row=2, sticky="nswe")
        button_2 = tk.Button(numkeys, text="2", command=lambda: self.add_num("2")).grid(column=1, row=2, sticky="nswe")
        button_3 = tk.Button(numkeys, text="3", command=lambda: self.add_num("3")).grid(column=2, row=2, sticky="nswe")

        button_del = tk.Button(numkeys, text="Del", command=lambda: self.del_num()).grid(column=0, row=3, sticky="nswe")
        button_0   = tk.Button(numkeys, text="0", command=lambda: self.add_num("0")).grid(column=1, row=3, sticky="nswe")
        button_ok  = tk.Button(numkeys, text="OK", command=lambda: self.enter_tel()).grid(column=2, row=3, sticky="nswe")


    def add_num(self, num):
        context.entry_text.set(context.entry_text.get() + num)


    def del_num(self):
        context.entry_text.set(context.entry_text.get()[:-1])

    def enter_tel(self):
        # FIXME: 入力内容によって処理が分岐するのは望ましくない。要:画面遷移の見直し
        if context.entry_caption.get() == u"会計金額入力":
            point_num = self.controller.frames["SalesEntry"].calc_point(context.entry_text.get())
            context.point_num.set(point_num)

        self.controller.show_frame(context.after_entry)


class Finish(tk.Frame):
    """完了
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        caption = tk.Label(self, textvariable=context.finish_message)
        caption.pack(side="top", fill="x")


    def show(self, message, duration = 3):
        """完了画面にメッセージを表示する
        @param duration 表示時間(単位は秒)
        """
        context.finish_message.set(message)
        self.controller.show_frame("Finish")
        self.after(duration * 1000, lambda: self.controller.show_frame("Menu"))


class MapApp(tk.Tk):

    # 画面
    SCREENS = (Menu, # メニュー
               CoupointScan, # クーポイントスキャン
               CoupointShow, # クーポイント詳細
               CmdSelect, # 流通ポイント処理選択
               CardSelect, # カード選択
               TelEntry, # 電話番号入力
               SalesEntry, # 会計金額入力
               NumKeys, # ソフトキーボード
               Finish, # 完了
               )

    def build(self):
        self.title("MAP")

        if APP_ENV == "Monmag":
            if not ON_DEBUG:
                self.attributes('-fullscreen', True) # 全画面・タイトルバー非表示
        else:
            self.geometry("{}x{}".format(WINDOW_WIDTH, WINDOW_HEIGHT))

        global default_font, header_font, body_font
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family="Droid Sans Japanese", size=FONT_SIZE)
        # print(font.families()) ###

        header_font = font.Font(self, family="Droid Sans Japanese", size=int(FONT_SIZE*0.8))
        body_font = font.Font(self, family="Droid Sans Japanese", size=int(FONT_SIZE*0.6))

        self.client_images = [] # 画像への参照をキープするために必須

        # container に画面(frame)を積んでおき、表示する画面を一番上に持ってくる
        container = tk.Frame(self)
        if APP_ENV == "Monmag":
            container.config(cursor='none')
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in MapApp.SCREENS:
            scr_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[scr_name] = frame

            frame.grid(row=0, column=0, sticky="nsew")

        # 初期表示画面
        self.show_frame("Menu")


    def show_frame(self, scr_name):
        frame = self.frames[scr_name]
        frame.tkraise()


    def debug(self, content):
        print(content)


class Context():

    def __init__(self):
        # 端末のシリアルナンバー
        self.serialno = None

        # 端末のMACアドレス
        self.macaddress = None

        # 選択されたカード(流通)
        self.selected_client = None

        # ソフトキーボード画面で"OK"を押した時に表示される画面
        self.after_entry = None

        # スキャンされたカードの番号
        self.scanned_card_no = None

        """"以下、ウィジェットと連携している変数"""

        # ソフトキーボード画面に表示する文言
        self.entry_caption = tk.StringVar()

        # ソフトキーボードで入力された値
        self.entry_text = tk.StringVar()

        # 付与するポイント
        self.point_num = tk.StringVar()

        # 完了画面に表示する文言
        self.finish_message = tk.StringVar()


    def get_serialno(self):
        if self.serialno is None:
            try:
                xml = ET.parse("/home/pi/Git/monmag-rpi/qrcode_reader/mqtt.xml")
            except IOError:
                xml = ET.parse("mqtt.xml")

            self.serialno = xml.find('deviceid').text

        return self.serialno


    def get_macaddress(self):
        if self.macaddress is None:
            try:
                file = open("/sys/class/net/wlan0/address", "r") # Monmag
            except IOError:
                file = open("macaddress", "r") # 開発用

            macaddress = str.strip(file.readline())
            file.close()

        return self.macaddress


if __name__ == "__main__":
    app = MapApp()
    context = Context()
    app.build()
    app.mainloop()

