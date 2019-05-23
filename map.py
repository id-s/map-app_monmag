import tkinter as tk
from tkinter import font
from tkinter import ttk

import os
import requests
import xml.etree.ElementTree as ET
from PIL import Image, ImageTk
from pprint import pprint

APP_ENV = os.getenv("APP_ENV", "Monmag")

WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320
PADDING = 4

if APP_ENV == "Monmag":
    FONT_SIZE = 19
else:
    FONT_SIZE = 24

IMAGE_DIR = "images"
SELECT_CARD_LIMIT = 5 # FIXME:delete 選択できるカードの種類数(上限)


class Menu(ttk.Frame):
    """メニュー画面
    """

    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller

        menu1 = ttk.Button(self, text="MyShopクーポイントをスキャンする",
                          command=lambda: controller.quit())
        menu2 = ttk.Button(self, text="流通会員カードをスキャンする",
                          command=lambda: controller.show_frame("CmdSelect"))

        menu1.pack()
        menu2.pack()


class CoupointScan(ttk.Frame):
    """クーポイントスキャン
    """

    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller

        label = ttk.Label(self, text="クーポイントをスキャンしてください")
        label.pack(side="top", fill="x")


class CmdSelect(ttk.Frame):
    """流通ポイント処理選択
    """

    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller

        button1 = ttk.Button(self, text="付与",
                          command=lambda: controller.show_frame("CardSelect"))
        button2 = ttk.Button(self, text="取消",
                          command=lambda: controller.show_frame("Menu"))

        button1.pack()
        button2.pack()


class CardSelect(ttk.Frame):
    """カード選択
    """

    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller

        clients = self.get_clients()
        if (clients):
            self.add_buttons(clients)


    def get_clients(self):
        """利用できるカードを取得する
        """
        url = "https://card-dot-my-shop-magee-stg.appspot.com/v1/check"
        headers = {"Content-Type": "application/json"}

        macaddress = self.controller.get_macaddress()
        print(macaddress) ###
        serialno = self.controller.get_serialno()
        print(serialno) ###
        data = {
            "terminal": { # TODO:端末情報取得
                "macaddr": "00:00:00:00:00:00",
                "serial_no": "YP000000000000",
                "device_id": "000000000000000",
                "version": "1.0.0",
            }
        }

        print("POST {}".format(url)) ###
        resp = requests.post(url, data=data, headers=headers)

        if resp.status_code == 200:
            print(resp.text) ###
            result = resp.json()
            return result["clients"]
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
            button = ttk.Button(self, compound="left", text=client["card_name"], image=image,
                                width=WINDOW_WIDTH - PADDING * 2,
                                command=self.select_card(client["client_cd"]))
            button.pack()
            #controller.card_select_buttons.append(button) # FIXME:delete


    def select_card(self, client_cd):
        """カード選択時の処理
        http://memopy.hatenadiary.jp/entry/2017/06/11/220452 を参考に実装した。
        """
        def func():
            print("Select card:{}".format(client_cd)) ###
            self.controller.show_frame("TelEntry")
        return func


class TelEntry(ttk.Frame):
    """電話番号入力
    """

    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller

        caption = tk.Label(self, text="初めてのご利用の方は進呈ポイントをショートメールでお知らせします。",
                           wraplength=(WINDOW_WIDTH - PADDING * 2), justify="left", height=2, padx=PADDING)
        caption.pack(side="top", fill="x")

        label = ttk.Label(self, text="電話番号入力")
        label.pack(side="top", fill="x")

        tel_entry = ttk.Entry(self, textvariable=self.controller.entry_text, font=default_font)
        tel_entry.pack(side="top", fill="x")

        button = ttk.Button(self, text="確定",
                            command=lambda: controller.quit())
        button.pack(side="top")
        button.focus_set()

        tel_entry.bind("<FocusIn>", self.show_num_keys)

    def show_num_keys(self, event):
        self.controller.show_frame("NumKeys")


class NumKeys(ttk.Frame):
    """ソフトキーボード
    """

    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        self.controller = controller

        caption = ttk.Label(self, text="電話番号入力")
        caption.pack(side="top", fill="x")

        entry = ttk.Entry(self, textvariable=self.controller.entry_text, font=default_font)
        entry.pack(side="top", fill="x")

        numkeys = ttk.Frame(self)
        numkeys.pack(side="top", fill="x")

        numkeys.columnconfigure(0, weight=1)
        numkeys.columnconfigure(1, weight=1)
        numkeys.columnconfigure(2, weight=1)

        button_7 = ttk.Button(numkeys, text="7", command=lambda: self.add_num("7")).grid(column=0, row=0, sticky="nswe")
        button_8 = ttk.Button(numkeys, text="8", command=lambda: self.add_num("8")).grid(column=1, row=0, sticky="nswe")
        button_9 = ttk.Button(numkeys, text="9", command=lambda: self.add_num("9")).grid(column=2, row=0, sticky="nswe")

        button_4 = ttk.Button(numkeys, text="4", command=lambda: self.add_num("4")).grid(column=0, row=1, sticky="nswe")
        button_5 = ttk.Button(numkeys, text="5", command=lambda: self.add_num("5")).grid(column=1, row=1, sticky="nswe")
        button_6 = ttk.Button(numkeys, text="6", command=lambda: self.add_num("6")).grid(column=2, row=1, sticky="nswe")

        button_1 = ttk.Button(numkeys, text="1", command=lambda: self.add_num("1")).grid(column=0, row=2, sticky="nswe")
        button_2 = ttk.Button(numkeys, text="2", command=lambda: self.add_num("2")).grid(column=1, row=2, sticky="nswe")
        button_3 = ttk.Button(numkeys, text="3", command=lambda: self.add_num("3")).grid(column=2, row=2, sticky="nswe")

        button_del = ttk.Button(numkeys, text="Del", command=lambda: self.del_num()).grid(column=0, row=3, sticky="nswe")
        button_0   = ttk.Button(numkeys, text="0", command=lambda: self.add_num("0")).grid(column=1, row=3, sticky="nswe")
        button_ok  = ttk.Button(numkeys, text="OK", command=lambda: self.enter_tel()).grid(column=2, row=3, sticky="nswe")


    def add_num(self, num):
        self.controller.entry_text.set(self.controller.entry_text.get() + num)


    def del_num(self):
        self.controller.entry_text.set(self.controller.entry_text.get()[:-1])

    def enter_tel(self):
        self.controller.show_frame("TelEntry")


class MapApp(tk.Tk):

    # 画面
    SCREENS = (Menu, # メニュー
               CoupointScan, # クーポイントスキャン
               CmdSelect, # 流通ポイント処理選択
               CardSelect, # カード選択
               TelEntry, # 電話番号入力
               NumKeys, # ソフトキーボード
               )

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title("MAP")

        self.attributes('-topmost', True) # NG:タイトルバー非表示
        if APP_ENV == "Monmag":
            self.attributes('-fullscreen', True) # 全画面・タイトルバー非表示
        else:
            self.geometry("{}x{}".format(WINDOW_WIDTH, WINDOW_HEIGHT))

        style = ttk.Style()
#         print(style.theme_names()) # ('aqua', 'clam', 'alt', 'default', 'classic')
#         style.theme_use("clam") # デフォルトは'aqua'
        global default_font
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family="Droid Sans Japanese", size=FONT_SIZE)
#         print(font.families()) ###
        style.configure("TButton", padding=FONT_SIZE/2)
#         pprint(style.layout("TButton"))

        self.entry_text = tk.StringVar()
        self.client_images = [] # 画像への参照をキープするために必須
#         self.card_select_buttons = [] # FIXME:delete

        # container に画面(frame)を積んでおき、表示する画面を一番上に持ってくる
        container = ttk.Frame(self)
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


    def get_serialno(self):
        serialno = None
        try:
            xml = ET.parse("/home/pi/Git/monmag-rpi/qrcode_reader/mqtt.xml")
        except FileNotFoundError:
            xml = ET.parse("mqtt.xml")

        serialno = xml.find('deviceid').text

        return serialno


    def get_macaddress(self):
        macaddress = None
        try:
            file = open("/sys/class/net/wlan0/address", "r") # Monmag
        except FileNotFoundError:
            file = open("macaddress", "r") # 開発用

        macaddress = str.strip(file.readline())
        file.close()

        return macaddress


    def debug(self, content):
        print(content)


if __name__ == "__main__":
    app = MapApp()
    app.mainloop()

