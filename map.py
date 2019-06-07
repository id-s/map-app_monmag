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
import textwrap
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from PIL import Image, ImageTk
from pprint import pprint
from pyzbar import pyzbar

APP_ENV = os.getenv("APP_ENV", "Monmag")
ON_DEBUG = os.getenv("ON_DEBUG", False)

locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')

WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320

IMAGE_DIR = "images"
SOUND_DIR = "sounds"


class Menu(tk.Frame):
    """メニュー画面
    """

    def __init__(self, parent):
        # FIXME: 画面の上下を反転させたいが指定不可？　他同様の画面あり
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="メニュー")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        menu1_button = tk.Button(self, text="MyShopクーポイントをスキャンする",command=self.menu1_button_clicked)
        menu1_button.configure(style.default_button)
        menu1_button.pack(fill="x")

        menu2_button = tk.Button(self, text="流通会員カードをスキャンする",command=self.menu2_button_clicked)
        menu2_button.configure(style.default_button)
        menu2_button.pack(fill="x")

        menu3_button = tk.Button(self, text="設定",command=self.menu3_button_clicked)
        menu3_button.configure(style.default_button)
        menu3_button.pack(fill="x", side="bottom")


    def menu1_button_clicked(self):
        app.play("button")

        if api.check_coupoint():
            app.frames["CoupointScan"].show()
        else:
            app.showerror("クーポイントエラー", "この店舗でご利用できるクーポイントはありません。")


    def menu2_button_clicked(self):
        app.play("button")
        app.frames["CardSelect"].show("add")


    def show_cmd_select(self):
        """@deprecated 操作手順短縮のため、CardSelectへ直行するようにしました。
        """
        app.play("button")

        # context.exec_nameは次の画面で決定する
        app.show_frame("CmdSelect")


    def menu3_button_clicked(self):
        app.play("button")
        app.show_frame("Setting")


class CoupointScan(tk.Frame):
    """クーポイントスキャン
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        text_label = tk.Label(self, text="クーポイントをスキャンしてください。")
        text_label.configure(style.default_label)
        text_label.pack(fill="x")

        if context.on_preview:
            self.preview = tk.Canvas(self, width = style.preview_width, height = style.preview_height, bg=style.preview_background)
            self.preview.pack()

        cancel_button = tk.Button(self, text="キャンセル", command=self.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.pack(fill="x", side="bottom")

#         self.bind("<Activate>", self.start_scan) # Monmagではこのイベントが発生しない


    def start_scan(self, event = None):
        app.log("start_scan")
        self.on_scan = True
        self.capture = cv2.VideoCapture(0)
        self.after(100, self.scan)


    def scan(self):
        if not self.on_scan:
            return
        ret, frame = self.capture.read()
        if not ret:
            app.log("No capture", "WARNING")
            return

        app.log("Scan start")
        self.image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if APP_ENV == "Monmag" and context.on_preview:
            self.image = self.image.transpose(1,0,2)[::-1] # -90度回転、詳細は https://qiita.com/matsu_mh/items/54b09273aef79ae027bc 参照
        self.decoded = pyzbar.decode(self.image)
        if self.decoded:
            for code in self.decoded:
                app.log(code, "INFO")
                self.after_scan(code.data)
#                 self.preview.create_text(style.preview_offset_x, style.preview_offset_y, text=code.data, tag="code") ###
                return

        if context.on_preview:
            self.image = Image.fromarray(self.image)
            self.image = ImageTk.PhotoImage(self.image)
    #         app.log("w:{} x h:{}".format(self.image.width(), self.image.height())) ###
            self.preview.create_image(style.preview_offset_x, style.preview_offset_y, image=self.image)
        app.log("Scan end")

        self.after(100, self.scan)


    def after_scan(self, data):
        app.log("after_scan")
        coupoint_show = app.frames["CoupointShow"]
        decoded_data = coupoint_show.parse_decoded_data(data)

        if decoded_data:
            app.play("success")
            self.on_scan = False
            self.capture.release()
            app.frames["CoupointShow"].show(decoded_data)
        else:
            app.showerror("クーポイントエラー", "このQRコードはクーポイントではありません。")

            self.after(500, self.scan)


    def show(self):
        context.exec_name = "coupoint"
        app.frames["CoupointScan"].start_scan()
        app.show_frame(self)


    def back_menu(self):
        app.log("back_menu")
        app.play("button")

        self.on_scan = False
        if context.on_preview:
            self.preview.delete("code")
        self.capture.release()
        context.exec_name = None
        app.show_frame("Menu")


class CoupointShow(tk.Frame):
    """クーポイント詳細表示
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)


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


    def show_coupoint(self, coupoint):

        self.title_label = tk.Label(self, text="来店ポイントプレゼント")
        self.title_label.configure(style.title_label)
        self.title_label.pack(fill="x")

        self.use_term_label = tk.Label(self, text="利用可能期間", font=style.header_font, anchor="w")
        self.use_term_label.configure(style.default_label)
        self.use_term_label.pack(fill="x")

        use_term_from = datetime.strptime(coupoint["use_term_from"], "%Y-%m-%d %H:%M:%S").strftime("%Y年%B%d日(%A)")
        use_term_to = datetime.strptime(coupoint["use_term_to"], "%Y-%m-%d %H:%M:%S").strftime("%Y年%B%d日(%A)")
        self.use_term_text = tk.Label(self, text="{} 〜 {}".format(use_term_from, use_term_to), font=style.body_font, justify="left")
        self.use_term_text.configure(style.default_label)
        self.use_term_text.pack(fill="x")

        self.use_button = tk.Button(self, text="利用確定", command=self.use_coupoint)
        self.use_button.configure(style.primary_button)
        self.use_button.pack(fill="x", side="bottom")


    def clear_coupoint(self):
        self.title_label.destroy()
        self.use_term_label.destroy()
        self.use_term_text.destroy()
        self.use_button.destroy()


    def use_coupoint(self):
        app.play("button")

        self.clear_coupoint()
        context.finish_message.set("MyShopポイントを付与しました。")
        app.frames["Finish"].show()


    def show(self, decoded_data):
        coupoint = api.get_coupoint(decoded_data)
        self.show_coupoint(coupoint)
        app.show_frame(self)


class CmdSelect(tk.Frame):
    """@deprecated 操作手順短縮のため、取消フローを設定画面へ移しました。
       流通ポイント処理選択
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        add_point_button = tk.Button(self, text="ポイント付与", command=self.add_point_button_clicked)
        add_point_button.configure(style.default_button)
        add_point_button.pack(fill="x")

        cancel_point_button = tk.Button(self, text="ポイント取消", command=self.cancel_point_button_clicked)
        cancel_point_button.configure(style.default_button)
        cancel_point_button.pack(fill="x")

        cancel_button = tk.Button(self, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.pack(fill="x")


    def add_point_button_clicked(self):
        app.play("button")

        context.exec_name = "add_point"
        context.sales_entry_button_text.set("付与確定")
        context.finish_message.set("流通ポイントを付与しました。")
        app.show_frame("CardSelect")


    def cancel_point_button_clicked(self):
        app.play("button")

        context.exec_name = "cancel_point"
        context.sales_entry_button_text.set("取消確定")
        context.finish_message.set("付与した流通ポイントを取消しました。")
        app.show_frame("CardSelect")


class CardSelect(tk.Frame):
    """カード選択
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="カード選択")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        clients = api.get_clients()
        if (clients):
            self.add_buttons(clients)


    def add_buttons(self, clients):
        for client in clients:
            resp = requests.get(client["img_url"], stream=True)
            if resp.status_code != 200:
                continue
            file_path = os.path.join(IMAGE_DIR, "{}.png".format(client["client_cd"]))
            with open(file_path, "wb") as f:
                f.write(resp.content)
                app.log("Download image: {}".format(file_path), "INFO")

            image = Image.open(file_path)
            image = ImageTk.PhotoImage(image.resize((48, 48)))
            app.client_images.append(image)
            button = tk.Button(self, text=client["card_name"], image=image, compound="left", command=self.select_card(client["client_cd"]))
            button.configure(style.default_button)
            button.pack(fill="x")

        button = tk.Button(self, text="キャンセル", command=app.back_menu)
        button.configure(style.default_button)
        button.pack(fill="x", side="bottom")


    def select_card(self, client_cd):
        """カード選択時の処理
        http://memopy.hatenadiary.jp/entry/2017/06/11/220452 を参考に実装した。
        """
        def func():
            app.play("button")

            app.log("Select card:{}".format(client_cd))
            context.selected_client = client_cd

            app.show_frame("CardScan")

        return func


    def show(self, mode="add"):
        if mode == "add":
            context.exec_name = "add_point"
            context.sales_entry_button_text.set("付与確定")
            context.finish_message.set("流通ポイントを付与しました。")
        elif mode == "cancel":
            context.exec_name = "cancel_point"
            context.sales_entry_button_text.set("取消確定")
            context.finish_message.set("付与した流通ポイントを取消しました。")
        else:
            raise MapAppException("Invalid mode:{}".format(mode))

        app.show_frame(self)


class CardScan(tk.Frame):
    """カードスキャン
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        text_label = tk.Label(self, text="カードをスキャンしてください。")
        text_label.configure(style.default_label)
        text_label.pack(fill="x")

        actions = tk.Frame(self)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.pack(fill="x", side="bottom")

        next_button = tk.Button(actions, text="(次へ)", command=self.next_button_clicked)
        next_button.configure(style.primary_button)
        next_button.grid(column=0, row=0, sticky="nswe")

        cancel_button = tk.Button(actions, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.grid(column=1, row=0, sticky="nswe")


    def next_button_clicked(self):
        app.play("button")
        app.frames["SalesEntry"].show_num_keys()


class Policy1(tk.Frame):
    """ポリシー表示1
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        text = """
            お得なクーポン満載「MyShop」への入会案内メッセージを携帯電話にお送りしますか？

            事業者名：マギー株式会社
            個人情報保護管理者：○○本部長 XXX-XXX-XXXX

            入力された情報は、本目的のみに利用いたします。
            """
        text_label = tk.Label(self, text=textwrap.dedent(text), font=style.body_font,
                              wraplength=(WINDOW_WIDTH - style.padding * 2), justify="left", height=8, padx=style.padding)
        text_label.configure(style.default_label)
        text_label.pack(fill="x")

        actions = tk.Frame(self)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.pack(fill="x", side="bottom")

        next_button = tk.Button(actions, text="次へ", command=self.next_button_clicked)
        next_button.configure(style.primary_button)
        next_button.grid(column=0, row=0, sticky="nswe")

        cancel_button = tk.Button(actions, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.grid(column=1, row=0, sticky="nswe")


    def next_button_clicked(self):
        app.play("button")
        app.show_frame("Policy2")


class Policy2(tk.Frame):
    """ポリシー表示2
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        text = """
            （続き）
            入力された情報の第三者提供は行いません。本事業の運用業務を他社に委託する場合があります。
            情報のご提供は任意です。ご提供いただけない場合、MyShopサービスへの入会案内メッセージはお送りいたしません。
            """
        text_label = tk.Label(self, text=textwrap.dedent(text), font=style.body_font,
                              wraplength=(WINDOW_WIDTH - style.padding * 2), justify="left", height=8, padx=style.padding)
        text_label.configure(style.default_label)
        text_label.pack(fill="x")

        actions = tk.Frame(self)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.pack(fill="x", side="bottom")

        next_button = tk.Button(actions, text="同意する", command=self.next_button_clicked)
        next_button.configure(style.primary_button)
        next_button.grid(column=0, row=0, sticky="nswe")

        cancel_button = tk.Button(actions, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.grid(column=1, row=0, sticky="nswe")


    def next_button_clicked(self):
        app.play("button")

        context.entry_caption.set("電話番号入力")
        context.after_entry = "TelEntry"
        app.frames["TelEntry"].show_num_keys()


class TelEntry(tk.Frame):
    """電話番号入力
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

#         caption = tk.Label(self, text="初めてのご利用の方は進呈ポイントをショートメールでお知らせします。",
#                            wraplength=(WINDOW_WIDTH - style.padding * 2), justify="left", height=2, padx=style.padding)
#         caption.configure(style.default_label)
#         caption.pack(fill="x")

        title_label = tk.Label(self, text="電話番号入力")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        tel_entry = tk.Entry(self, textvariable=context.entry_text, font=style.default_font)
        tel_entry.pack(fill="x")

        text_label = tk.Label(self, text="上記電話番号にショートメールでお知らせします。",
                              wraplength=(WINDOW_WIDTH - style.padding * 2), justify="left", height=2, padx=style.padding)
        text_label.configure(style.default_label)
        text_label.pack(fill="x")

        actions = tk.Frame(self)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.pack(side="bottom", fill="x")

        next_button = tk.Button(actions, text="確定", command=self.next_button_clicked)
        next_button.configure(style.primary_button)
        next_button.grid(column=0, row=0, sticky="nswe")

        cancel_button = tk.Button(actions, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.grid(column=1, row=0, sticky="nswe")

        tel_entry.bind("<FocusIn>", self.show_num_keys)


    def show_num_keys(self, event = None):
        context.entry_caption.set("電話番号入力")
        context.after_entry = "TelEntry"
        app.show_frame("NumKeys", False)


    def next_button_clicked(self):
        app.play("button")
        app.frames["Finish"].show()


    def show(self):
        app.show_frame(self)


class SalesEntry(tk.Frame):
    """会計金額入力
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="会計金額入力")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        sales_entry = tk.Entry(self, textvariable=context.entry_text, font=style.default_font)
        sales_entry.pack(fill="x")

        point_label = tk.Label(self, text="ポイント")
        point_label.configure(style.default_label)
        point_label.pack(fill="x")

        point_entry = tk.Entry(self, textvariable=context.point_num, font=style.default_font)
        point_entry.pack(fill="x")

        actions = tk.Frame(self)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.pack(side="bottom", fill="x")

        next_button = tk.Button(actions, textvariable=context.sales_entry_button_text, command=self.next_button_clicked)
        next_button.configure(style.primary_button)
        next_button.grid(column=0, row=0, sticky="nswe")

        cancel_button = tk.Button(actions, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.grid(column=1, row=0, sticky="nswe")

        sales_entry.bind("<FocusIn>", self.show_num_keys)


    def show_num_keys(self, event = None):
        context.entry_caption.set("会計金額入力")
        context.after_entry = "SalesEntry"
        app.show_frame("NumKeys", False)


    def next_button_clicked(self):
        app.play("button")

        context.entry_text.set("")
        if context.exec_name == "add_point":
            result = api.check_card()
            if result == "tel":
                app.show_frame("Policy1")
            elif result == "price":
                app.frames["Finish"].show()
            else:
                app.showerror("エラー", "エラーが発生しました。")

        elif context.exec_name == "cancel_point":
            app.frames["Finish"].show()


    def show(self):
        point_num = api.calc_point(context.entry_text.get())
        context.point_num.set(point_num)
        app.show_frame(self)


class NumKeys(tk.Frame):
    """ソフトキーボード
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, textvariable=context.entry_caption)
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        entry = tk.Entry(self, textvariable=context.entry_text, font=style.default_font)
        entry.pack(fill="x")

        keyboard = tk.Frame(self)
        keyboard.pack(fill="x")

        keyboard.columnconfigure(0, weight=1)
        keyboard.columnconfigure(1, weight=1)
        keyboard.columnconfigure(2, weight=1)

        num_buttons = [
                [
                    tk.Button(keyboard, text="7", command=lambda: self.add_num("7")),
                    tk.Button(keyboard, text="8", command=lambda: self.add_num("8")),
                    tk.Button(keyboard, text="9", command=lambda: self.add_num("9")),
                    ],
                [
                    tk.Button(keyboard, text="4", command=lambda: self.add_num("4")),
                    tk.Button(keyboard, text="5", command=lambda: self.add_num("5")),
                    tk.Button(keyboard, text="6", command=lambda: self.add_num("6")),
                    ],
                [
                    tk.Button(keyboard, text="1", command=lambda: self.add_num("1")),
                    tk.Button(keyboard, text="2", command=lambda: self.add_num("2")),
                    tk.Button(keyboard, text="3", command=lambda: self.add_num("3")),
                    ],
                [
                    tk.Button(keyboard, text="Del", command=lambda: self.del_num()),
                    tk.Button(keyboard, text="0",  command=lambda: self.add_num("0")),
                    tk.Button(keyboard, text="OK", command=self.button_ok_clicked),
                    ],
            ]

        for r in range(len(num_buttons)):
            row = num_buttons[r]
            for c in range(len(row)):
                button = row[c]
                button.configure(style.number_button)
                button.grid(column=c, row=r, sticky="nswe")

        num_buttons[3][0].configure(style.default_button) # Del
        num_buttons[3][0].configure(padx=num_buttons[3][1].cget("padx"), pady=num_buttons[3][1].cget("pady"))
        num_buttons[3][2].configure(style.primary_button) # OK
        num_buttons[3][2].configure(padx=num_buttons[3][1].cget("padx"), pady=num_buttons[3][1].cget("pady"))


    def add_num(self, num):
        app.play("button")
        context.entry_text.set(context.entry_text.get() + num)


    def del_num(self):
        app.play("button")
        context.entry_text.set(context.entry_text.get()[:-1])

    def button_ok_clicked(self):
        app.play("button")
        app.frames[context.after_entry].show()


class Finish(tk.Frame):
    """完了
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        message_label = tk.Label(self, textvariable=context.finish_message)
        message_label.configure(style.default_label)
        message_label.pack(fill="x")


    def show(self, duration = 3):
        """完了画面にメッセージを表示する
        @param duration 表示時間(単位は秒)
        """
        app.show_frame(self)
        context.clear(excepts=["finish_message"])
        self.after(duration * 1000, lambda: app.show_frame("Menu", False))


class Setting(tk.Frame):
    """設定
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="設定")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        cancel_point_button = tk.Button(self, text="ポイント取消", command=self.cancel_point_button_clicked)
        cancel_point_button.configure(style.default_button)
        cancel_point_button.pack(fill="x")

        wifi_button = tk.Button(self, text="Wi-Fi設定", state="disabled")
        wifi_button.configure(style.default_button)
        wifi_button.pack(fill="x")

        quit_button = tk.Button(self, text="アプリ終了", command=app.quit)
        quit_button.configure(style.default_button)
        quit_button.pack(fill="x")

        cancel_button = tk.Button(self, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.pack(fill="x", side="bottom")


    def cancel_point_button_clicked(self):
        app.play("button")
        app.frames["CardSelect"].show("cancel")


class MapApi():

    def check_coupoint(self):
        """クーポイント実施チェック
        """
        url = "https://qr-dot-my-shop-magee-stg.appspot.com/v1/check"
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": "48:a9:e9:dc:e2:65", # context.macaddress, # TODO:取得情報に差し替え
                "serial_no": "0123456789ABCDEF", # context.serialno,
                }
            }

        app.log("POST {}".format(url), "INFO")
        app.log(json.dumps(data), "INFO")
        resp = requests.post(url, data=json.dumps(data), headers=headers)

        if resp.status_code == 200:
            app.log(resp.text, "INFO")
            resp_data = resp.json()
            if resp_data["result"] == "success":
                return True
            else:
                return False
        else:
            app.log(resp.status_code, "WARNING")
            return False


    def get_coupoint(self, decoded_data):
        """クーポイントの詳細を取得する
        @param decoded_data QRコードから読み込まれたデータ(要parse)
        """
        url = "https://qr-dot-my-shop-magee-stg.appspot.com/v1/start"
        headers = {"Content-Type": "application/json"}

        app.log("customer_id:{}, carousel_id:{}".format(decoded_data["customer_id"], decoded_data["carousel_id"])) ###
        data = {
            "terminal": {
                "macaddr": "48:a9:e9:dc:e2:65", # context.macaddress, # TODO:取得情報に差し替え
                "serial_no": "0123456789ABCDEF", # context.serialno,
                },
            "carousel": {
                "customer_id": "20b097add4aea673e074d77fe1495434", # TODO:取得情報に差し替え
                "carousel_id": "327765a3ec00962ccc050e91354dcc64",
                }
            }

        app.log("POST {}".format(url), "INFO")
        app.log(json.dumps(data), "INFO")
        resp = requests.post(url, data=json.dumps(data), headers=headers)

        if resp.status_code == 200:
            app.log(resp.text, "INFO")
            resp_data = resp.json()
            if resp_data["result"] == "regist":
                return resp_data["carousel"]
            else:
                app.log(resp_data["result"], "WARNING")
                return None
        else:
            app.log(resp.status_code, "WARNING")
            return None


    def get_clients(self):
        """利用できるカードを取得する
        """
        url = "https://card-dot-my-shop-magee-stg.appspot.com/v1/check"
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": "48:a9:e9:dc:e2:65", # context.macaddress, # TODO:取得情報に差し替え
                "serial_no": "0123456789ABCDEF", # context.serialno,
                }
            }

        app.log("POST {}".format(url), "INFO")
        app.log(json.dumps(data), "INFO")
        resp = requests.post(url, data=json.dumps(data), headers=headers)

        if resp.status_code == 200:
            app.log(resp.text, "INFO")
            resp_data = resp.json()
            return resp_data["clients"]
        else:
            app.log(resp.status_code, "WARNING")
            return None


    def calc_point(self, sales):
        """付与ポイント算出
        """
        url = "https://card-dot-my-shop-magee-stg.appspot.com/v1/calc"
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": "48:a9:e9:dc:e2:65", # context.macaddress, # TODO:取得情報に差し替え
                "serial_no": "0123456789ABCDEF", # context.serialno,
                },
            "customer": {
                "card_no": "CRC0S0 32840000000000200001", # TODO:取得情報に差し替え
                "price": sales,
                "client_cd": context.selected_client,
                "card_id": 1,
                }
            }

        app.log("POST {}".format(url), "INFO")
        app.log(json.dumps(data), "INFO")
        resp = requests.post(url, data=json.dumps(data), headers=headers)

        if resp.status_code == 200:
            app.log(resp.text, "INFO")
            resp_data = resp.json()
            if resp_data["result"]:
                return resp_data["result"]
            else:
                return None
        else:
            app.log(resp.status_code, "WARNING")
            return None


    def check_card(self):
        """カードのチェック
        @return "tel": 初回利用(次に電話番号入力画面を表示)
                "price": 二回目以降の利用(次に会計金額入力画面を表示)
                "failure": カード読み込み不正（選択された流通と読み込まれたカードが一致しない等）
                 None: サーバエラーなど
        """
        url = "https://card-dot-my-shop-magee-stg.appspot.com/v1/start"
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": "48:a9:e9:dc:e2:65", # context.macaddress, # TODO:取得情報に差し替え
                "serial_no": "0123456789ABCDEF", # context.serialno,
                },
            "customer": {
                "card_no": "CRC0S0 32840000000000200001", # TODO:取得情報に差し替え
                "client_cd": context.selected_client,
                "card_id": 1,
                }
            }

        app.log("POST {}".format(url), "INFO")
        app.log(json.dumps(data), "INFO")
        resp = requests.post(url, data=json.dumps(data), headers=headers)

        if resp.status_code == 200 or resp.status_code == 404:
            app.log(resp.text, "INFO")
            resp_data = resp.json()
            return resp_data["result"]
        else:
            app.log(resp.status_code, "WARNING")
            return None


class MapApp(tk.Tk):

    # 画面
    SCREENS = (Menu, # メニュー
               CoupointScan, # クーポイントスキャン
               CoupointShow, # クーポイント詳細
               CmdSelect, # 流通ポイント処理選択
               CardSelect, # カード選択
               CardScan, # カードスキャン
               Policy1, # ポリシー表示1
               Policy2, # ポリシー表示2
               TelEntry, # 電話番号入力
               SalesEntry, # 会計金額入力
               NumKeys, # ソフトキーボード
               Finish, # 完了
               Setting, # 設定
               )


    def build(self):
        self.title("MAP")

        if APP_ENV == "Monmag":
            if not ON_DEBUG:
                self.attributes('-fullscreen', True) # 全画面・タイトルバー非表示
        else:
            self.geometry("{}x{}".format(WINDOW_WIDTH, WINDOW_HEIGHT))

        # プレビューのタイムラグが問題になるようなら、下記フラグをFalseにする
        context.on_preview = True

        self.client_images = [] # 画像への参照をキープするために必須

        # container に画面(frame)を積んでおき、表示する画面を一番上に持ってくる
        container = tk.Frame(self)
        if APP_ENV == "Monmag":
            container.config(cursor='none')
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in MapApp.SCREENS:
            screen_name = F.__name__
            frame = F(parent=container)
            self.frames[screen_name] = frame

            frame.configure(style.screen)
            frame.grid(row=0, column=0, sticky="nsew")

        # 初期表示画面
        self.show_frame("Menu")


    def show_frame(self, screen, check_show = True):
        """指定された画面を表示する
        @param screen string or Frame
        """
        if isinstance(screen, tk.Frame):
            check_show = False
            screen = screen.__class__.__name__
        app.log("Show {}".format(screen))

        frame = self.frames[screen]
        if check_show and hasattr(frame, "show"):
            raise MapAppException("'{}' should use `show()`".format(screen))
        frame.tkraise()


    def back_menu(self):
        app.play("button")

        context.exec_name = None
        app.show_frame("Menu")


    def showerror(self, title, message):
        """エラーダイアログを表示する
        """
        app.play("failure")

        # FIXME: ダイアログの最大化ボタン他を消したいが、指定不可？　他同様
        messagebox.showerror(title, message)


    def beep(self):
        """ビープ音を鳴らす
        @deprecated: Monmag(Raspberry Pi)ではこの方法で鳴らせませんでした。
        """
        if APP_ENV == "Monmag":
            print("\007")


    def play(self, sound_name):
        """サウンドを再生する
        """
        if APP_ENV == "Monmag":
            sound_file = os.path.abspath(os.path.join(SOUND_DIR, "{}.wav".format(sound_name)))
            subprocess.call(["aplay", sound_file])


    def log(self, content, level="DEBUG"):
        """ログ出力
        """
        if (not ON_DEBUG) and level == "DEBUG":
            return
        print("{} [{}] {}".format(datetime.now(), level, content))


class Style():

    def __init__(self, app):
        if APP_ENV == "Monmag":
            self.font_size = 19
        else:
            self.font_size = 24

        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Droid Sans Japanese", size=self.font_size)
        # app.log(font.families()) ###

        self.header_font = font.Font(app, family="Droid Sans Japanese", size=int(self.font_size*0.8))
        self.body_font = font.Font(app, family="Droid Sans Japanese", size=int(self.font_size*0.8))

        self.base_color = "#e40023" # MyShopの基本色(ロゴより取得)
        self.base_color_S05 = "#e4d9da" # base_colorのSaturation(彩度)を"05"まで落とした色

        self.padding = 4

        self.screen = {"background":self.base_color_S05}

        self.button_borderwidth = 4
        self.button_relief = "raised"
        self.button_padx = 0
        self.button_pady = self.font_size / 4
        self.default_button = {
            "bg":"white", "activebackground":"white",
            "fg":self.base_color, "activeforeground":self.base_color,
            "highlightbackground":self.base_color_S05, "highlightcolor":self.base_color,
            "highlightthickness":self.button_borderwidth,
            "borderwidth":self.button_borderwidth, "relief":self.button_relief,
            "padx":self.button_padx, "pady":self.button_pady,
            }
        self.primary_button = {
            "bg":self.base_color, "activebackground":self.base_color,
            "fg":"white", "activeforeground":"white",
            "highlightbackground":self.base_color_S05, "highlightcolor":self.base_color,
            "highlightthickness":self.button_borderwidth,
            "borderwidth":self.button_borderwidth, "relief":self.button_relief,
            "padx":self.button_padx, "pady":self.button_pady,
            }
        self.number_button = {
            "bg":self.base_color_S05, "activebackground":self.base_color_S05,
            "fg":"black", "activeforeground":"black",
            "highlightbackground":self.base_color_S05, "highlightcolor":self.base_color,
            "highlightthickness":self.button_borderwidth,
            "borderwidth":self.button_borderwidth, "relief":self.button_relief,
            }

        self.default_label = {"background":self.base_color_S05}
        self.title_label = {"background":"white"}

        self.preview_width = 320
        self.preview_height = 200
        self.preview_offset_x = self.preview_width / 2 + 64
        self.preview_offset_y = self.preview_height / 2 + 64
        self.preview_background = "black"


class Context():

    def __init__(self):
        # 端末のシリアルナンバー
        self.serialno = self._get_serialno()

        # 端末のMACアドレス
        self.macaddress = self._get_serialno()

        # 実行中の処理名
        self.exec_name = None

        # プレビュー表示フラグ
        self.on_preview = True

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

        # 金額入力画面のボタンに表示する文言
        self.sales_entry_button_text = tk.StringVar()

        # 完了画面に表示する文言
        self.finish_message = tk.StringVar()


    def clear(self, excepts=[]):
        if not "exec_name" in excepts:
            self.exec_name = None

        if not "on_preview" in excepts:
            self.on_preview = True

        if not "selected_client" in excepts:
            self.selected_client = None

        if not "after_entry" in excepts:
            self.after_entry = None

        if not "scanned_card_no" in excepts:
            self.scanned_card_no = None

        if not "entry_caption" in excepts:
            self.entry_caption.set("")

        if not "entry_text" in excepts:
            self.entry_text.set("")

        if not "point_num" in excepts:
            self.point_num.set("")

        if not "sales_entry_button_text" in excepts:
            self.sales_entry_button_text.set("")

        if not "finish_message" in excepts:
            self.finish_message.set("")


    def _get_serialno(self):
        try:
            xml = ET.parse("/home/pi/Git/monmag-rpi/qrcode_reader/mqtt.xml")
        except IOError:
            xml = ET.parse("mqtt.xml")

        self.serialno = xml.find('deviceid').text

        return self.serialno


    def _get_macaddress(self):
        try:
            file = open("/sys/class/net/wlan0/address", "r") # Monmag
        except IOError:
            file = open("macaddress", "r") # 開発用

        macaddress = str.strip(file.readline())
        file.close()

        return self.macaddress


class MapAppException(Exception):
    pass


if __name__ == "__main__":
    app = MapApp()
    style = Style(app)
    context = Context()
    api = MapApi()

    app.build()
    app.mainloop()

