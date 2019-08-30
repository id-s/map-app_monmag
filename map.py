# -*- coding:utf-8 -*-

import Tkinter as tk
import tkFont as font
import tkMessageBox as messagebox
import ttk

import cv2
import json
import locale
import os
import re
import requests
import subprocess
import textwrap
import time
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime
from PIL import Image, ImageTk
from pipes import quote
from pprint import pprint
from pyzbar import pyzbar
from wifi import Cell, Scheme

APP_ENV = os.getenv("APP_ENV", "Monmag")
APP_MODE = os.getenv("APP_MODE", "normal")
ON_DEBUG = os.getenv("ON_DEBUG", False)

GOOGLE_TRACKING_ID = "UA-114507936-1" # MyShop
GOOGLE_TRACKING_HOST = "map.my-shop.fun" # ビューを分けるための擬似的なホスト名
USER_AGENT = "Magee/Monmag" # MonmagのUser-Agent

locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')

WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320

IMAGE_DIR = "images"
SOUND_DIR = "sounds"

WPA_SUPPLICANT_FILE = "/etc/wpa_supplicant/wpa_supplicant.conf"


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

        menu3_button = tk.Button(self, text="システム",command=self.menu3_button_clicked)
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
        app.show_frame("SystemMenu")


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

        try:
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

        except Exception as e:
            app.log(traceback.format_exc(), "ERROR")
            self.capture.release()
            app.quit()


    def parse_decoded_data(self, decoded_data):
        """QRコードで読み取った文字列をパースし、customer_id, carousel_idを取得する
        @see https://redmine.magee.co.jp/projects/myshop/wiki/%E3%82%AF%E3%83%BC%E3%83%9D%E3%82%A4%E3%83%B3%E3%83%88QR%E3%82%B3%E3%83%BC%E3%83%89%E3%81%AE%E4%BB%95%E6%A7%98
        """
        lines = decoded_data.split("\r\n")
        if context.app_mode == "test":
            context.customer_id = "20b097add4aea673e074d77fe1495434" # customer_id:100319
            context.carousel_id = "c56e7e7d0be1fd3eb72f25a7748b1109" # carousel_id:212
            return True

        elif (len(lines) == 4 and lines[0] == "MyShop"):
            context.customer_id = lines[1]
            context.carousel_id = lines[2]
            return True

        return False


    def after_scan(self, data):
        app.log("after_scan")
        result = self.parse_decoded_data(data)

        if result:
            app.play("success")
            self.on_scan = False
            self.capture.release()
            app.frames["CoupointShow"].show()
        else:
            app.showerror("クーポイントエラー", "このQRコードはクーポイントではありません。")

            self.after(500, self.scan)


    def show(self):
        app.frames["CoupointScan"].start_scan()
        app.show_frame(self)


    def back_menu(self):
        app.play("button")

        self.on_scan = False
        if context.on_preview:
            self.preview.delete("code")
        self.capture.release()
        context.reset()
        app.show_frame("Menu")


class CoupointShow(tk.Frame):
    """クーポイント詳細表示
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        actions = tk.Frame(self)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.pack(fill="x", side="bottom")

        self.next_button = tk.Button(actions)
        self.next_button.configure(style.primary_button)
        self.next_button.grid(column=0, row=0, sticky="nswe")

        cancel_button = tk.Button(actions, text="キャンセル", command=self.cancel_button_clicked)
        cancel_button.configure(style.default_button)
        cancel_button.grid(column=1, row=0, sticky="nswe")


    def show_coupoint(self, coupoint):

        self.title_label = tk.Label(self, text=coupoint["title"])
        self.title_label.configure(style.title_label)
        self.title_label.pack(fill="x")

        self.use_term_label = tk.Label(self, text="[利用可能期間]", font=style.header_font, anchor="w")
        self.use_term_label.configure(style.default_label)
        self.use_term_label.pack(fill="x")

        use_term_from = datetime.strptime(coupoint["use_term_from"], "%Y-%m-%d %H:%M:%S").strftime("%Y年%B%d日(%a)")
        use_term_to = datetime.strptime(coupoint["use_term_to"], "%Y-%m-%d %H:%M:%S").strftime("%Y年%B%d日(%a)")
        self.use_term_text = tk.Label(self, text="{} 〜 {}".format(use_term_from, use_term_to), font=style.body_font, justify="left")
        self.use_term_text.configure(style.default_label)
        self.use_term_text.pack(fill="x")

        self.description_label = tk.Label(self, text="[クーポイント内容]", font=style.header_font, anchor="w")
        self.description_text = tk.Label(self, text=coupoint["description"], font=style.body_font, justify="left", height=1)
        if (coupoint["description"]):
            self.description_label.configure(style.default_label)
            self.description_label.pack(fill="x")

            self.description_text.configure(style.default_label)
    #         self.description_text.configure(background="white")
            self.description_text.pack(fill="x")

            use_condition_height = 4

        else:
            use_condition_height = 6

        self.use_condition_text = tk.Label(self, text=u"[利用条件]\n" + coupoint["use_condition"], font=style.body_font,
                                           wraplength=(WINDOW_WIDTH - style.padding * 2), justify="left", height=use_condition_height, padx=style.padding)
        self.use_condition_text.configure(style.default_label)
#         self.use_condition_text.configure(background="white")
        self.use_condition_text.pack(fill="x")


    def clear_coupoint(self):
        if not hasattr(self, "title_label"):
            return

        self.title_label.destroy()
        self.use_term_label.destroy()
        self.use_term_text.destroy()
        self.description_label.destroy()
        self.description_text.destroy()
        self.use_condition_text.destroy()


    def use_coupoint(self):
        app.play("button")

        result = api.use_coupoint()
        if result == "success":
            context.finish_message.set("MyShopポイントを付与しました。")
            app.frames["Finish"].show()
        else:
            app.showerror("エラー", "エラーが発生しました。")


    def cancel_coupoint(self):
        app.play("button")

        result = api.cancel_coupoint()
        if result == "success":
            context.finish_message.set("付与したMyShopポイントを取消しました。")
            app.frames["Finish"].show()
        else:
            app.showerror("エラー", "エラーが発生しました。")


    def cancel_button_clicked(self):
        app.play("button")
        app.back_menu()


    def show(self):
        self.clear_coupoint()

        result, coupoint = api.get_coupoint()
        if result == "regist":
            context.exec_name = "use_coupoint"
            self.next_button.configure(text="利用確定", command=self.use_coupoint)
        elif result == "cancel":
            context.exec_name = "cancel_coupoint"
            self.next_button.configure(text="利用キャンセル", command=self.cancel_coupoint)
        else:
            app.showerror("エラー", "エラーが発生しました。")
            app.back_menu()
            return

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

        self.card_buttons = []
        self.add_buttons()

        cancel_button = tk.Button(self, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.pack(fill="x", side="bottom")


    def add_buttons(self):
        clients = api.get_clients()
        if not clients:
            return False

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

            self.card_buttons.append(button)

        return True


    def reset_buttons(self):
        for button in self.card_buttons:
            button.destroy()

        return self.add_buttons()


    def select_card(self, client_cd):
        """カード選択時の処理
        http://memopy.hatenadiary.jp/entry/2017/06/11/220452 を参考に実装した。
        """
        def func():
            app.play("button")

            app.log("Select card:{}".format(client_cd))
            context.selected_client = client_cd

            app.frames["CardScan"].show()

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

        title_label = tk.Label(self, text="カードスキャン")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        text_label = tk.Label(self, text="カードをスキャンしてください。")
        text_label.configure(style.default_label)
        text_label.pack(fill="x")

        self.cardno_entry = tk.Entry(self, textvariable=context.scanned_no, show="*",
                                background=style.base_color_S05,
                                borderwidth=0, highlightthickness=0,
                                insertbackground=style.base_color_S05, insertborderwidth=0,
                                selectbackground=style.base_color_S05, selectborderwidth=0,
                                )
        self.cardno_entry.pack(fill="x")

        self.cardno_entry.bind("<Return>", self.card_scanned)

        actions = tk.Frame(self)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.pack(fill="x", side="bottom")

        self.next_button = tk.Button(actions, text="番号入力", command=self.entry_button_clicked)
        self.next_button.configure(style.primary_button)

        self.cancel_button = tk.Button(actions, text="キャンセル", command=app.back_menu)
        self.cancel_button.configure(style.default_button)

#         self.reset_buttons()
        self.next_button.grid(column=0, row=0, sticky="nswe")
        self.cancel_button.grid(column=1, row=0, sticky="nswe")


    def entry_button_clicked(self):
        app.play("button")
        app.frames["CardEntry"].show_num_keys()


    def reset_buttons(self):
        """@deprecated 手入力機能追加により、本機能は不要となりました。
        """
        if context.app_mode == "test":
            self.cancel_button.pack_forget()

            self.next_button.grid(column=0, row=0, sticky="nswe")
            self.cancel_button.grid(column=1, row=0, sticky="nswe")

        else:
            self.next_button.grid_forget()
            self.cancel_button.grid_forget()

            self.cancel_button.pack(fill="x", side="bottom")

        return True


    def next_button_clicked(self):
        """@deprecated 手入力機能追加により、本機能は無効となりました。
        """
        app.play("button")

        if context.app_mode == "test":
            context.card_no = "CRC0S0 32840000000000200001" # 下1桁を変えてもOK
        else:
            context.card_no = context.scanned_no.get()

        app.log("Entered card:{}".format(context.card_no))

        context.card_status = api.check_card()
        if context.card_status == "failure":
            context.finish_message.set("このカードはご利用できません。")
            app.frames["Finish"].show()
            return
        elif context.card_status is None:
            context.finish_message.set("エラーが発生しました。")
            app.frames["Finish"].show()
            return

        app.frames["SalesEntry"].show_num_keys()


    def card_scanned(self, event):
        app.play("success")

        context.card_no = context.scanned_no.get()
        app.log("Scanned card:{}".format(context.card_no), "INFO")

        context.card_status = api.check_card()
        if context.card_status == "failure":
            context.finish_message.set("このカードはご利用できません。")
            app.frames["Finish"].show()
            return
        elif context.card_status is None:
            context.finish_message.set("エラーが発生しました。")
            app.frames["Finish"].show()
            return

        if context.exec_name == "add_point":
            app.frames["SalesEntry"].show_num_keys()
            return
        elif context.exec_name == "cancel_point":
            app.frames["HistorySelect"].show()
            return
        else:
            app.log("Illegal exec_name: {}".format(context.exec_name), "WARNING")


    def show(self):
        self.cardno_entry.focus_set()
        app.show_frame(self)


class CardEntry(tk.Frame):
    """カード番号確認
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="カード番号確認")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        card_entry = tk.Entry(self, textvariable=context.entry_text, font=style.default_font)
        card_entry.pack(fill="x")

        self.text_label = tk.Label(self, text="上記カードにポイントを付与します。",
                                   wraplength=(WINDOW_WIDTH - style.padding * 2), justify="left", height=2, padx=style.padding)
        self.text_label.configure(style.default_label)
        self.text_label.pack(fill="x")

        actions = tk.Frame(self)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.pack(side="bottom", fill="x")

        self.next_button = tk.Button(actions, text="確定", command=self.next_button_clicked)
        self.next_button.configure(style.primary_button)
        self.next_button.grid(column=0, row=0, sticky="nswe")

        cancel_button = tk.Button(actions, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.grid(column=1, row=0, sticky="nswe")

        card_entry.bind("<FocusIn>", self.show_num_keys)


    def show_num_keys(self, event = None):
        context.entry_caption.set("カード番号入力")
        context.after_entry = "CardEntry"
        app.show_frame("NumKeys")


    def next_button_clicked(self):
        app.play("button")

        context.card_status = api.check_card()
        if context.card_status == "failure":
            context.finish_message.set("このカードはご利用できません。")
            app.frames["Finish"].show()
            return
        elif context.card_status is None:
            context.finish_message.set("エラーが発生しました。")
            app.frames["Finish"].show()
            return

        if (context.card_no):
            if context.exec_name == "add_point":
                context.entry_caption.set("会計金額入力")
                context.entry_text.set("")
                context.after_entry = "SalesEntry"
                app.show_frame("NumKeys")
                return

            elif context.exec_name == "cancel_point":
                app.frames["HistorySelect"].show()
                return

            else:
                app.log("Illegal exec_name: {}".format(context.exec_name), "WARNING")

        else:
            app.showerror("エラー", "カード番号を入力してください。")


    def show(self):
        context.card_no = context.entry_text.get()
        if context.exec_name == "add_point":
            self.text_label.configure(text="上記カードにポイントを付与します。")
        elif context.exec_name == "cancel_point":
            self.text_label.configure(text="上記カードに付与されたポイントをキャンセルします。")
        self.next_button.focus_set()
        app.show_frame(self)


class DeviceSelect(tk.Frame):
    """機器選択
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="機器選択")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        text_label = tk.Label(self, text="ご利用の携帯電話を選択してください。")
        text_label.configure(style.default_label)
        text_label.pack(fill="x")

        iphone_select_button = tk.Button(self, text="スマートフォン(iPhone)", command=lambda: self.select_button_clicked(1))
        iphone_select_button.configure(style.default_button)
        iphone_select_button.pack(fill="x")

        android_select_button = tk.Button(self, text="スマートフォン(iPhone以外)", command=lambda: self.select_button_clicked(2))
        android_select_button.configure(style.default_button)
        android_select_button.pack(fill="x")

        other_select_button = tk.Button(self, text="スマートフォン以外", command=lambda: self.select_button_clicked(0))
        other_select_button.configure(style.default_button)
        other_select_button.pack(fill="x")

        none_select_button = tk.Button(self, text="持っていない", command=self.cancel_button_clicked)
        none_select_button.configure(style.default_button)
        none_select_button.pack(fill="x")

        cancel_button = tk.Button(self, text="キャンセル", command=self.cancel_button_clicked)
        cancel_button.configure(style.default_button)
        cancel_button.pack(fill="x", side="bottom")


    def select_button_clicked(self, device_type):
        app.play("button")

        context.device_type = device_type
        app.show_frame("Policy1")


    def cancel_button_clicked(self):
        app.play("button")

        context.device_type = -1

        # キャンセルでもポイント付与は必要
        result = api.add_point()
        if (result == "success"):
            app.frames["Finish"].show()
        else:
            app.showerror("エラー", "エラーが発生しました。")


class Policy1(tk.Frame):
    """ポリシー表示1
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        text = """
            ポイント付与通知・お得なクーポン満載「MyShop」への入会案内メッセージを携帯電話にお送りしますか？

            事業者名：マギー株式会社
            個人情報保護管理者：代表取締役社長 098-951-0915
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

        cancel_button = tk.Button(actions, text="キャンセル", command=self.cancel_button_clicked)
        cancel_button.configure(style.default_button)
        cancel_button.grid(column=1, row=0, sticky="nswe")


    def next_button_clicked(self):
        app.play("button")
        app.show_frame("Policy2")


    def cancel_button_clicked(self):
        app.play("button")

        # 電話番号入力キャンセルでもポイント付与は必要
        result = api.add_point()
        if (result == "success"):
            app.frames["Finish"].show()
        else:
            app.showerror("エラー", "エラーが発生しました。")


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
            入力された情報は、本目的のみに利用いたします。
            入力された情報の第三者提供は行いません。本事業の運用業務を他社に委託する場合があります。
            情報のご提供は任意です。ご提供いただけない場合、ポイント付与通知・MyShopサービスへの入会案内メッセージはお送りいたしません。
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

        cancel_button = tk.Button(actions, text="キャンセル", command=self.cancel_button_clicked)
        cancel_button.configure(style.default_button)
        cancel_button.grid(column=1, row=0, sticky="nswe")


    def next_button_clicked(self):
        app.play("button")

        context.entry_caption.set("電話番号入力")
        context.entry_text.set("")
        context.after_entry = "TelEntry"
        app.frames["TelEntry"].show_num_keys()


    def cancel_button_clicked(self):
        app.play("button")

        # 電話番号入力キャンセルでもポイント付与は必要
        result = api.add_point()
        if (result == "success"):
            app.frames["Finish"].show()
        else:
            app.showerror("エラー", "エラーが発生しました。")


class TelEntry(tk.Frame):
    """電話番号確認
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="電話番号確認")
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

        self.next_button = tk.Button(actions, text="確定", command=self.next_button_clicked)
        self.next_button.configure(style.primary_button)
        self.next_button.grid(column=0, row=0, sticky="nswe")

        cancel_button = tk.Button(actions, text="キャンセル", command=self.cancel_button_clicked)
        cancel_button.configure(style.default_button)
        cancel_button.grid(column=1, row=0, sticky="nswe")

        tel_entry.bind("<FocusIn>", self.show_num_keys)


    def show_num_keys(self, event = None):
        context.entry_caption.set("電話番号入力")
        context.after_entry = "TelEntry"
        app.show_frame("NumKeys")


    def next_button_clicked(self):
        app.play("button")

        result = api.add_point()
        if (result == "success"):
            app.frames["Finish"].show()
        else:
            app.showerror("エラー", "エラーが発生しました。")


    def cancel_button_clicked(self):
        app.play("button")

        # 電話番号入力キャンセルでもポイント付与は必要
        result = api.add_point()
        if (result == "success"):
            app.frames["Finish"].show()
        else:
            app.showerror("エラー", "エラーが発生しました。")


    def show(self):
        context.tel = context.entry_text.get()
        self.next_button.focus_set()
        app.show_frame(self)


class SalesEntry(tk.Frame):
    """会計金額確認
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="会計金額確認")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        self.sales_entry = tk.Entry(self, textvariable=context.entry_text, font=style.default_font)
        self.sales_entry.pack(fill="x")

        point_label = tk.Label(self, text="ポイント")
        point_label.configure(style.default_label)
        point_label.pack(fill="x")

        point_entry = tk.Entry(self, textvariable=context.point_num, font=style.default_font)
        point_entry.pack(fill="x")

        actions = tk.Frame(self)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.pack(side="bottom", fill="x")

        self.next_button = tk.Button(actions, textvariable=context.sales_entry_button_text, command=self.next_button_clicked)
        self.next_button.configure(style.primary_button)
        self.next_button.grid(column=0, row=0, sticky="nswe")

        cancel_button = tk.Button(actions, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.grid(column=1, row=0, sticky="nswe")


    def show_num_keys(self, event = None):
        context.entry_caption.set("会計金額入力")
        context.after_entry = "SalesEntry"
        app.show_frame("NumKeys")


    def next_button_clicked(self):
        app.play("button")

        if context.point_num.get() == "0":
            app.showerror("エラー", "付与されるポイントが0で間違いなければ[キャンセル]を押してください。")
            return

        if context.exec_name == "add_point":
            if context.card_status == "tel":
                app.show_frame("DeviceSelect")
            elif context.card_status == "price":
                result = api.add_point()
                if (result == "success"):
                    app.frames["Finish"].show()
                else:
                    app.showerror("エラー", "エラーが発生しました。")
            else:
                app.showerror("エラー", "エラーが発生しました。")

        elif context.exec_name == "cancel_point":
            result = api.cancel_point()
            if (result == "success"):
                app.frames["Finish"].show()
            else:
                app.showerror("エラー", "エラーが発生しました。")


    def show(self):
        if context.exec_name == "add_point":
            context.price = context.entry_text.get()
            point_num = api.calc_point()
            if point_num is None:
                app.showerror("エラー", "エラーが発生しました。")
                self.next_button.configure(state="disabled")
                point_num = "0"
            elif point_num == 0:
                self.next_button.configure(state="disabled")
            else:
                self.next_button.configure(state="normal")
            context.point_num.set(point_num)
            self.sales_entry.bind("<FocusIn>", self.show_num_keys)

        elif context.exec_name == "cancel_point":
            # 処理は全てHistorySelect.select_history()で済み
            self.next_button.configure(state="normal")
            self.sales_entry.unbind("<FocusIn>")

        self.next_button.focus_set()
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


class HistorySelect(tk.Frame):
    """履歴選択
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="履歴選択")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        self.history_buttons = []

        cancel_button = tk.Button(self, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.pack(fill="x", side="bottom")


    def add_buttons(self):
        histories = api.get_history()
        if not histories:
            return False

        for history in histories:
            button_label = "{} {}pt".format(history["scan_date"], history["point"])
            button = tk.Button(self, text=button_label, compound="left",
                               command=self.select_history(history["scan_card_history_id"], history["price"], history["point"]))
            button.configure(style.default_button)
            button.pack(fill="x")

            self.history_buttons.append(button)

        return True


    def reset_buttons(self):
        for button in self.history_buttons:
            button.destroy()

        return self.add_buttons()


    def select_history(self, scan_card_history_id, price, point):
        """履歴選択時の処理
        """
        def func():
            app.play("button")

            app.log("Select scan_card_history_id:{}".format(scan_card_history_id))
            context.scan_card_history_id = scan_card_history_id
            context.entry_text.set(price)
            context.price = price
            context.point_num.set(point)
            app.frames["SalesEntry"].show()

        return func


    def show(self):
        self.reset_buttons()
        app.show_frame(self)


class Finish(tk.Frame):
    """完了
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        message_label = tk.Label(self, textvariable=context.finish_message,
                                 wraplength=(WINDOW_WIDTH - style.padding * 2), justify="left", height=2, padx=style.padding)
        message_label.configure(style.default_label)
        message_label.pack(fill="x")


    def show(self, duration = 3):
        """完了画面にメッセージを表示する
        @param duration 表示時間(単位は秒)
        """
        app.show_frame(self)
        context.reset(excepts=["finish_message"])
        self.after(duration * 1000, lambda: app.show_frame("Menu", False))


class SystemMenu(tk.Frame):
    """システムメニュー
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="システム")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        cancel_point_button = tk.Button(self, text="ポイント取消", command=self.cancel_point_button_clicked)
        cancel_point_button.configure(style.default_button)
        cancel_point_button.pack(fill="x")

        setting_button = tk.Button(self, text="設定", command=self.setting_button_clicked)
        setting_button.configure(style.default_button)
        setting_button.pack(fill="x")

        cancel_button = tk.Button(self, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.pack(fill="x", side="bottom")


    def cancel_point_button_clicked(self):
        app.play("button")
        app.frames["CardSelect"].show("cancel")


    def setting_button_clicked(self):
        app.play("button")
        app.show_frame("Setting")


class Setting(tk.Frame):
    """設定
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="設定")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        if APP_ENV == "Monmag":
            wifi_button = tk.Button(self, text="Wi-Fi設定", command=self.wifi_button_clicked)
        else:
            wifi_button = tk.Button(self, text="Wi-Fi設定", state="disabled")
        wifi_button.configure(style.default_button)
        wifi_button.pack(fill="x")

        switch_mode_button = tk.Button(self, text="モード切り替え", command=self.switch_mode_button_clicked)
        switch_mode_button.configure(style.default_button)
        switch_mode_button.pack(fill="x")

        quit_button = tk.Button(self, text="アプリ終了", command=app.quit)
        quit_button.configure(style.default_button)
        quit_button.pack(fill="x")

        remote_connect_button = tk.Button(self, text="リモート接続", command=self.remote_connect_button_clicked)
        remote_connect_button.configure(style.default_button)
        remote_connect_button.pack(fill="x")

        cancel_button = tk.Button(self, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.pack(fill="x", side="bottom")


    def wifi_button_clicked(self):
        app.play("button")
        app.frames["WifiScan"].show()


    def switch_mode_button_clicked(self):
        app.play("button")
        app.show_frame("SwitchMode")


    def remote_connect_button_clicked(self):
        app.play("button")
        app.show_frame("RemoteConnect")


class RemoteConnect(tk.Frame):
    """リモート接続
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="リモート接続")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        text_label = tk.Label(self, text="調査のため、Mageeからのリモート接続を受け入れます。(調査中は本端末をご利用いただけません)",
                              wraplength=(WINDOW_WIDTH - style.padding * 2), justify="left", height=3, padx=style.padding)
        text_label.configure(style.default_label)
        text_label.pack(fill="x")

        connect_button = tk.Button(self, text="接続する", command=self.connect_button_clicked)
        connect_button.configure(style.default_button)
        connect_button.pack(fill="x")

        cancel_button = tk.Button(self, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.pack(fill="x", side="bottom")


    def connect_button_clicked(self):
        app.play("button")

        funcs = [
            lambda: self.remote_connect(),
            lambda: self.remote_error()]
        app.frames["Progress"].show(funcs, "リモート接続中...")


    def remote_connect(self):
        app.set_fullscreen(False)
        app.update()

        command = "ngrok tcp -region jp --remote-addr={} 5900".format(context.ngrok_reserved_address)
        Util.exec_command(command)
        # ngrok接続中はこれ以上先へ進まない
        # 切断は端末の再起動を想定

        return True


    def remote_error(self):
        app.set_fullscreen(True)

        context.finish_message.set("接続に失敗しました。")
        return True


class SwitchMode(tk.Frame):
    """モード切り替え
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="モード切り替え")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        self.text_label = tk.Label(self, text=self.get_mode_text())
        self.text_label.configure(style.default_label)
        self.text_label.pack(fill="x")

        normal_mode_button = tk.Button(self, text="通常モード", command=lambda: self.mode_button_clicked("normal"))
        normal_mode_button.configure(style.default_button)
        normal_mode_button.pack(fill="x")

        test_mode_button = tk.Button(self, text="テストモード", command=lambda: self.mode_button_clicked("test"))
        test_mode_button.configure(style.default_button)
        test_mode_button.pack(fill="x")

        cancel_button = tk.Button(self, text="キャンセル", command=app.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.pack(fill="x", side="bottom")


    def get_mode_name(self):
        if context.app_mode == "normal":
            return "通常"
        elif context.app_mode == "test":
            return "テスト"
        else:
            return ""


    def get_mode_text(self):
        return "現在は「{}」モードです。".format(self.get_mode_name())


    def mode_button_clicked(self, mode):
        app.play("button")

        context.app_mode = mode
        context.reset()
        api.reset()
        self.text_label.configure(text=self.get_mode_text())

        success = app.frames["CardSelect"].reset_buttons()
        if not success:
            app.showerror("エラー", "カード情報の取得に失敗しました。")

#         success = app.frames["CardScan"].reset_buttons()
#         if not success:
#             app.showerror("エラー", "カードスキャン画面の更新に失敗しました。")

        app.log("Swith mode -> {}".format(context.app_mode), "INFO")
        context.finish_message.set("「{}」モードへ変更しました。".format(self.get_mode_name()))
        app.frames["Finish"].show()


class WifiScan(tk.Frame):
    """Wi-Fi設定
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="Wi-Fi設定")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        text_label = tk.Label(self, text="QRコードをスキャンしてください。")
        text_label.configure(style.default_label)
        text_label.pack(fill="x")

        if context.on_preview:
            self.preview = tk.Canvas(self, width = style.preview_width, height = style.preview_height, bg=style.preview_background)
            self.preview.pack()

        cancel_button = tk.Button(self, text="キャンセル", command=self.back_menu)
        cancel_button.configure(style.default_button)
        cancel_button.pack(fill="x", side="bottom")


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

        try:
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

            self.after(500, self.scan)

        except Exception as e:
            app.log(traceback.format_exc(), "ERROR")
            self.capture.release()
            app.quit()


    def parse_decoded_data(self, decoded_data):
        """QRコードで読み取った文字列をパースし、ssid,passwordを取得する
        """
        parsed_data = {}
        lines = decoded_data.split("/")
        if len(lines) > 0:
            parsed_data["ssid"] = lines[0]
        if len(lines) > 1:
            parsed_data["password"] = lines[1]
        else:
            parsed_data["password"] = None
        return parsed_data


    def ap_setting(self, decoded_data):
        command = "grep \"{}\" {}".format(decoded_data["ssid"], WPA_SUPPLICANT_FILE)
        result = Util.exec_command(command)
        if (result is None) or (result == ""):
            Util.append_wpa_supplicant(decoded_data["ssid"], decoded_data["password"])
        return True


    def wifi_setting(self, decoded_data):
        target = None
        for cell in Cell.all("wlan0"):
            app.log("ssid:{}, address:{}".format(cell.ssid, cell.address))
            if cell.encrypted:
                app.log("encryption_type:{}".format(cell.encryption_type))
            if cell.ssid == decoded_data["ssid"]:
                target = cell
                break
        if target is None:
            app.log("Not found ssid:{}".format(decoded_data["ssid"]), "WARNING")
            return False

        scheme = Scheme.find("wlan0", decoded_data["ssid"])
        if scheme is None:
            app.log("Create scheme:{}".format(decoded_data["ssid"]), "INFO")
            scheme = Scheme.for_cell("wlan0", decoded_data["ssid"], target, decoded_data["password"])
            scheme.save()

        scheme.activate() # アプリをsudoで動かさないと"Permission denied"になる
        return True


    def wifi_finish(self):
        context.finish_message.set("Wi-Fi設定が完了しました。")
        return True


    def after_scan(self, data):
        app.log("after_scan")
        parsed_data = self.parse_decoded_data(data)

        if parsed_data:
            app.play("success")
            app.log("Scanned:{}".format(parsed_data), "INFO")

            self.on_scan = False
            self.capture.release()

            funcs = [
                lambda: self.ap_setting(parsed_data),
                lambda: self.wifi_setting(parsed_data),
                lambda: self.wifi_finish()]
            app.frames["Progress"].show(funcs, "Wi-Fi設定中...")

        else:
            app.showerror("エラー", "Wi-Fi設定が取得できませんでした。")
            self.after(500, self.scan)


    def show(self):
        app.frames["WifiScan"].start_scan()
        app.show_frame(self)


    def back_menu(self):
        app.play("button")

        self.on_scan = False
        if context.on_preview:
            self.preview.delete("code")
        self.capture.release()
        context.reset()
        app.show_frame("Menu")


class Progress(tk.Frame):
    """進捗表示
    """

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        title_label = tk.Label(self, text="進捗表示")
        title_label.configure(style.title_label)
        title_label.pack(fill="x")

        self.text_label = tk.Label(self)
        self.text_label.configure(style.default_label)
        self.text_label.pack(fill="x")

        self.bar = ttk.Progressbar(self, length=400, mode="determinate")
        self.bar.pack()


    def show(self, funcs, text=""):
        """画面を表示する
        @param funcs 画面表示中に行う処理(関数)を配列で渡す。
                     処理結果がTrueの場合、次の処理へ進む。次の処理がなければ完了画面へ。
                     処理結果がFalseもしくは例外がスローされると以降の処理はキャンセルされ、メニューへ戻る
        """
        bar_value = 0
        self.bar.configure(maximum=len(funcs), value=bar_value)
        self.text_label.configure(text=text)
        app.show_frame(self)
        app.update()

        try:
            context.finish_message.set("処理が完了しました。")
            for func in funcs:
                bar_value += 1
                self.bar.configure(value=bar_value)
                app.update()

                result = func()
                if not result:
                    raise MapAppException("処理を中断します。")

            self.after(500, app.frames["Finish"].show)

        except Exception as e:
            app.log(traceback.format_exc(), "WARNING")
            app.showerror("エラー", e.message)
            app.back_menu()


class Measurement():
    """Google Measurement Protocol(Google Analytics)
    """

    def __init__(self, client_id):
        self.endpoint = "https://www.google-analytics.com/collect"
        self.common_payload = {
            "v": 1,
            "tid": GOOGLE_TRACKING_ID,
            "cid": client_id,
            "ds": "term",
            }

    def report(self, data):
        payload = dict(self.common_payload, **data)
        app.log("Measurement Protocol payload: {}".format(payload))
        try:
            headers = {"User-Agent": USER_AGENT} # 必須
            resp = requests.post(self.endpoint, data=payload, headers=headers)
            app.log(resp)

        except Exception as e:
            app.log(traceback.format_exc(), "WARNING")


    def report_event(self, category, action, options = {}):
        payload = {"t":"event", "ec":category, "ea":action}
        data = dict(payload, **options)
        self.report(data)


    def report_pageview(self, screen_name, options = {}):
        payload = {"t":"pageview", "dh":GOOGLE_TRACKING_HOST, "dp":Util.conv_path(screen_name), "dt":screen_name}
        data = dict(payload, **options)
        self.report(data)


class MapApi():

    def __init__(self):
        self.reset()


    def reset(self):
        """実行モードに応じて設定を切り替える
        """
        app.log("Reset api", "INFO")

        if context.app_mode == "test":
            self.check_coupoint_url  = "https://qr-dot-my-shop-magee-stg.appspot.com/v1/check"
            self.get_coupoint_url    = "https://qr-dot-my-shop-magee-stg.appspot.com/v1/start"
            self.use_coupoint_url    = "https://qr-dot-my-shop-magee-stg.appspot.com/v1/regist"
            self.cancel_coupoint_url = "https://qr-dot-my-shop-magee-stg.appspot.com/v1/cancel"
            self.get_clients_url     = "https://card-dot-my-shop-magee-stg.appspot.com/v1/check"
            self.check_card_url      = "https://card-dot-my-shop-magee-stg.appspot.com/v1/start"
            self.calc_point_url      = "https://card-dot-my-shop-magee-stg.appspot.com/v1/calc"
            self.add_point_url       = "https://card-dot-my-shop-magee-stg.appspot.com/v1/regist"
            self.cancel_point_url    = "https://card-dot-my-shop-magee-stg.appspot.com/v1/cancel"
            self.get_history_url     = "https://card-dot-my-shop-magee-stg.appspot.com/v1/history"

        else:
            self.check_coupoint_url  = "https://qr-dot-my-shop-magee.appspot.com/v1/check"
            self.get_coupoint_url    = "https://qr-dot-my-shop-magee.appspot.com/v1/start"
            self.use_coupoint_url    = "https://qr-dot-my-shop-magee.appspot.com/v1/regist"
            self.cancel_coupoint_url = "https://qr-dot-my-shop-magee.appspot.com/v1/cancel"
            self.get_clients_url     = "https://card-dot-my-shop-magee.appspot.com/v1/check"
            self.check_card_url      = "https://card-dot-my-shop-magee.appspot.com/v1/start"
            self.calc_point_url      = "https://card-dot-my-shop-magee.appspot.com/v1/calc"
            self.add_point_url       = "https://card-dot-my-shop-magee.appspot.com/v1/regist"
            self.cancel_point_url    = "https://card-dot-my-shop-magee.appspot.com/v1/cancel"
            self.get_history_url     = "https://card-dot-my-shop-magee.appspot.com/v1/history"


    def check_coupoint(self):
        """クーポイント実施チェック
        """
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": context.macaddress,
                "serial_no": context.serialno,
                }
            }

        app.log("POST {}".format(self.check_coupoint_url), "INFO")
        app.log(json.dumps(data), "INFO")
        try:
            resp = requests.post(self.check_coupoint_url, data=json.dumps(data), headers=headers)

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

        except Exception as e:
            app.log(traceback.format_exc(), "WARNING")
            return False


    def get_coupoint(self):
        """クーポイントの詳細を取得する
        """
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": context.macaddress,
                "serial_no": context.serialno,
                },
            "carousel": {
                "customer_id": context.customer_id,
                "carousel_id": context.carousel_id,
                }
            }

        app.log("POST {}".format(self.get_coupoint_url), "INFO")
        app.log(json.dumps(data), "INFO")
        try:
            resp = requests.post(self.get_coupoint_url, data=json.dumps(data), headers=headers)

            if resp.status_code == 200:
                app.log(resp.text, "INFO")
                resp_data = resp.json()
                return resp_data["result"], resp_data["carousel"]
            else:
                app.log(resp.status_code, "WARNING")
                return None, None

        except Exception as e:
            app.log(traceback.format_exc(), "WARNING")
            return None, None


    def use_coupoint(self):
        """クーポイントを利用する
        """
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": context.macaddress,
                "serial_no": context.serialno,
                },
            "carousel": {
                "customer_id": context.customer_id,
                "carousel_id": context.carousel_id,
                }
            }

        app.log("POST {}".format(self.use_coupoint_url), "INFO")
        app.log(json.dumps(data), "INFO")
        try:
            resp = requests.post(self.use_coupoint_url, data=json.dumps(data), headers=headers)

            if resp.status_code == 200 or resp.status_code == 404:
                app.log(resp.text, "INFO")
                if resp.status_code == 200:
                    measurement.report_event("MAP", "use-coupoint")
                resp_data = resp.json()
                return resp_data["result"]
            else:
                app.log(resp.status_code, "WARNING")
                return None

        except Exception as e:
            app.log(traceback.format_exc(), "WARNING")
            return None


    def cancel_coupoint(self):
        """クーポイントを利用キャンセルする
        """
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": context.macaddress,
                "serial_no": context.serialno,
                },
            "carousel": {
                "customer_id": context.customer_id,
                "carousel_id": context.carousel_id,
                }
            }

        app.log("POST {}".format(self.cancel_coupoint_url), "INFO")
        app.log(json.dumps(data), "INFO")
        try:
            resp = requests.post(self.cancel_coupoint_url, data=json.dumps(data), headers=headers)

            if resp.status_code == 200 or resp.status_code == 404:
                app.log(resp.text, "INFO")
                if resp.status_code == 200:
                    measurement.report_event("MAP", "cancel-coupoint")
                resp_data = resp.json()
                return resp_data["result"]
            else:
                app.log(resp.status_code, "WARNING")
                return None

        except Exception as e:
            app.log(traceback.format_exc(), "WARNING")
            return None


    def get_clients(self):
        """利用できるカードを取得する
        """
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": context.macaddress,
                "serial_no": context.serialno,
                }
            }

        app.log("POST {}".format(self.get_clients_url), "INFO")
        app.log(json.dumps(data), "INFO")
        try:
            resp = requests.post(self.get_clients_url, data=json.dumps(data), headers=headers)

            if resp.status_code == 200:
                app.log(resp.text, "INFO")
                resp_data = resp.json()
                if resp_data["result"] == "success":
                    return resp_data["clients"]
                else:
                    return None
            else:
                app.log(resp.status_code, "WARNING")
                return None

        except Exception as e:
            app.log(traceback.format_exc(), "WARNING")
            return None


    def check_card(self):
        """カードのチェック
        @return "tel": 初回利用(次に電話番号入力画面を表示)
                "price": 二回目以降の利用(次に会計金額入力画面を表示)
                "failure": カード読み込み不正（選択された流通と読み込まれたカードが一致しない等）
                 None: サーバエラーなど
        """
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": context.macaddress,
                "serial_no": context.serialno,
                },
            "customer": {
                "card_no": context.card_no,
                "client_cd": context.selected_client,
                }
            }

        app.log("POST {}".format(self.check_card_url), "INFO")
        app.log(json.dumps(data), "INFO")
        try:
            resp = requests.post(self.check_card_url, data=json.dumps(data), headers=headers)

            if resp.status_code == 200 or resp.status_code == 404:
                app.log(resp.text, "INFO")
                resp_data = resp.json()
                return resp_data["result"]
            else:
                app.log(resp.status_code, "WARNING")
                return None

        except Exception as e:
            app.log(traceback.format_exc(), "WARNING")
            return None


    def calc_point(self):
        """付与ポイント算出
        """
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": context.macaddress,
                "serial_no": context.serialno,
                },
            "customer": {
                "card_no": context.card_no,
                "price": context.price,
                "client_cd": context.selected_client,
                }
            }

        app.log("POST {}".format(self.calc_point_url), "INFO")
        app.log(json.dumps(data), "INFO")
        try:
            resp = requests.post(self.calc_point_url, data=json.dumps(data), headers=headers)

            if resp.status_code == 200:
                app.log(resp.text, "INFO")
                resp_data = resp.json()
                return resp_data["result"]
            else:
                app.log(resp.status_code, "WARNING")
                return None

        except Exception as e:
            app.log(traceback.format_exc(), "WARNING")
            return None


    def add_point(self):
        """ポイント付与＆電話番号登録
        """
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": context.macaddress,
                "serial_no": context.serialno,
                },
            "customer": {
                "card_no": context.card_no,
                "client_cd": context.selected_client,
                "price": context.price,
                "point": context.point_num.get(),
                "tel": context.tel,
                }
            }
        if context.device_type is not None: # `if context.device_type`だけだと 0 がFalseと判定されるので
            data["customer"]["device_type"] = context.device_type

        app.log("POST {}".format(self.add_point_url), "INFO")
        app.log(json.dumps(data), "INFO")
        try:
            resp = requests.post(self.add_point_url, data=json.dumps(data), headers=headers)

            if resp.status_code == 200 or resp.status_code == 404:
                app.log(resp.text, "INFO")
                if resp.status_code == 200:
                    measurement.report_event("MAP", "add-point")
                resp_data = resp.json()
                return resp_data["result"]
            else:
                app.log(resp.status_code, "WARNING")
                return None

        except Exception as e:
            app.log(traceback.format_exc(), "WARNING")
            return None


    def cancel_point(self):
        """ポイント付与キャンセル
        """
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": context.macaddress,
                "serial_no": context.serialno,
                },
            "customer": {
                "card_no": context.card_no,
                "client_cd": context.selected_client,
                "scan_card_history_id": context.scan_card_history_id,
                }
            }

        app.log("POST {}".format(self.cancel_point_url), "INFO")
        app.log(json.dumps(data), "INFO")
        try:
            resp = requests.post(self.cancel_point_url, data=json.dumps(data), headers=headers)

            if resp.status_code == 200 or resp.status_code == 404:
                app.log(resp.text, "INFO")
                if resp.status_code == 200:
                    measurement.report_event("MAP", "cancel-point")
                resp_data = resp.json()
                return resp_data["result"]
            else:
                app.log(resp.status_code, "WARNING")
                return None

        except Exception as e:
            app.log(traceback.format_exc(), "WARNING")
            return None


    def get_history(self):
        """ポイント付与履歴取得
        """
        headers = {"Content-Type": "application/json"}

        data = {
            "terminal": {
                "macaddr": context.macaddress,
                "serial_no": context.serialno,
                },
            "customer": {
                "card_no": context.card_no,
                "client_cd": context.selected_client,
                }
            }

        app.log("POST {}".format(self.get_history_url), "INFO")
        app.log(json.dumps(data), "INFO")
        try:
            resp = requests.post(self.get_history_url, data=json.dumps(data), headers=headers)

            if resp.status_code == 200:
                app.log(resp.text, "INFO")
                resp_data = resp.json()
                return resp_data["scan_card_histories"]
            else:
                app.log(resp.status_code, "WARNING")
                return None

        except Exception as e:
            app.log(traceback.format_exc(), "WARNING")
            return None


class MapApp(tk.Tk):

    # 画面
    SCREENS = (Menu, # メニュー
               CoupointScan, # クーポイントスキャン
               CoupointShow, # クーポイント詳細
               CmdSelect, # 流通ポイント処理選択
               CardSelect, # カード選択
               CardScan, # カードスキャン
               CardEntry, # カード番号確認
               DeviceSelect, # 機器選択
               Policy1, # ポリシー表示1
               Policy2, # ポリシー表示2
               TelEntry, # 電話番号確認
               SalesEntry, # 会計金額確認
               NumKeys, # ソフトキーボード
               HistorySelect, # 履歴選択
               Finish, # 完了
               SystemMenu, # システムメニュー
               Setting, # 設定
               RemoteConnect, # リモート接続
               SwitchMode, # モード切り替え
               WifiScan, # Wi-Fi設定
               Progress, # 進捗表示
               )


    def set_fullscreen(self, fullscreen=True):
        if APP_ENV == "Monmag":
            if not ON_DEBUG:
                self.attributes('-fullscreen', fullscreen) # 全画面・タイトルバー非表示
        else:
            self.geometry("{}x{}".format(WINDOW_WIDTH, WINDOW_HEIGHT))


    def build(self):
        self.title("MAP")

        self.set_fullscreen()

        # プレビューのタイムラグが問題になるようなら、下記フラグをFalseにする
        context.on_preview = False # プレビュー非表示

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

        frame = self.frames[screen]
        if check_show and hasattr(frame, "show"):
            raise MapAppException("'{}' should use `show()`".format(screen))

        app.log("Show {}".format(screen))
        measurement.report_pageview(screen)
        frame.tkraise()


    def back_menu(self):
        app.play("button")

        context.reset()
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
        # 実行モード
        self.app_mode = APP_MODE

        # 端末のシリアルナンバー
        self.serialno = self._get_serialno()

        # 端末のMACアドレス
        self.macaddress = self._get_macaddress()

        # ngrokでリモート接続するために予約しているアドレス
        self.ngrok_reserved_address = self._get_ngrok_reserved_address()

        # 実行中の処理名
        self.exec_name = None

        # プレビュー表示フラグ
        self.on_preview = True

        # カスタマーID
        self.customer_id = None

        # クーポイントID
        self.carousel_id = None

        # 選択された履歴ID
        self.scan_card_history_id = None

        # 選択されたカード(流通)
        self.selected_client = None

        # カード番号
        self.card_no = None

        # カードステータス
        self.card_status = None

        # 電話番号
        self.tel = None

        # 携帯電話種別
        self.device_type = None

        # 会計金額
        self.price = None

        # ソフトキーボード画面で"OK"を押した時に表示される画面
        self.after_entry = None

        """"以下、ウィジェットと連携している変数"""

        # スキャンされたカードの番号
        self.scanned_no = tk.StringVar()

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


    def reset(self, excepts=[]):
        if not excepts:
            app.log("Reset all context", "INFO")

        if not "serialno" in excepts:
            self.serialno = self._get_serialno()

        if not "macaddress" in excepts:
            self.macaddress = self._get_macaddress()

        if not "macaddress" in excepts:
            self.ngrok_reserved_address = self._get_ngrok_reserved_address()

        if not "exec_name" in excepts:
            self.exec_name = None

        # on_preview はアプリ作動中にリセットされないものとする

        if not "customer_id" in excepts:
            self.customer_id = None

        if not "carousel_id" in excepts:
            self.carousel_id = None

        if not "scan_card_history_id" in excepts:
            self.scan_card_history_id = None

        if not "selected_client" in excepts:
            self.selected_client = None

        if not "card_no" in excepts:
            self.card_no = None

        if not "card_status" in excepts:
            self.card_status = None

        if not "tel" in excepts:
            self.tel = None

        if not "device_type" in excepts:
            self.device_type = None

        if not "price" in excepts:
            self.price = None

        if not "after_entry" in excepts:
            self.after_entry = None

        if not "scanned_no" in excepts:
            self.scanned_no.set("")

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
        if self.app_mode == "test":
            return "0123456789ABCDEF"

        try:
            xml = ET.parse("/home/pi/Git/monmag-rpi/qrcode_reader/mqtt.xml") # Monmag
        except IOError:
            xml = ET.parse("mqtt.xml") # 開発用

        serialno = xml.find('deviceid').text

        return serialno


    def _get_macaddress(self):
        if self.app_mode == "test":
            return "48:a9:e9:dc:e2:65"

        try:
            file = open("/sys/class/net/wlan0/address", "r") # Monmag
        except IOError:
            file = open("macaddress", "r") # 開発用

        macaddress = str.strip(file.readline())
        file.close()

        return macaddress


    def _get_ngrok_reserved_address(self):
        file = open("ngrok_reserved_address", "r")
        ngrok_reserved_address = str.strip(file.readline())
        file.close()

        return ngrok_reserved_address


class Util():

    @staticmethod
    def exec_command(command):
        """Linuxコマンドを実行する
        """
        app.log("Exec command: {}".format(command), "INFO")
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if stderr:
            app.log(stderr, "WARNING")
            raise MapAppException(stderr)
        if stdout:
            app.log(stdout, "INFO")
            return stdout


    @staticmethod
    def append_wpa_supplicant(ssid, passphrase, scan_ssid = 1):
        """ /etc/wpa_supplicant/wpa_supplicant.conf にAP情報を追加する
        """
        indent = " " * 8
        content = "network={\n"
        content += indent + "ssid=\"{}\"\n".format(ssid)
        if (passphrase is None) or (passphrase == ""):
            content += indent + "key_mgmt=NONE\n"
        else:
            content += indent + "psk=\"{}\"\n".format(passphrase)
            content += indent + "key_mgmt=WPA-PSK\n"
        content += "}\n\n"
        app.log(content)

        command = "echo {} | tee -a {}".format(quote(content), WPA_SUPPLICANT_FILE)
        result = Util.exec_command(command)
        app.log(result)


    @staticmethod
    def conv_snakecase(name):
        """スネークケース(snake_case)に変換する
        @see http://hatakazu.hatenablog.com/entry/2013/02/16/135911
        """
        return re.sub("([A-Z])",lambda x:"_" + x.group(1).lower(),name)


    @staticmethod
    def conv_path(name):
        """大文字を"/"に変換することで、パスっぽい文字列に変換する
        例) HogePiyo -> /hoge/piyo
        """
        return re.sub("([A-Z])",lambda x:"/" + x.group(1).lower(),name)


class MapAppException(Exception):
    pass


if __name__ == "__main__":
    app = MapApp()
    style = Style(app)
    context = Context()
    measurement = Measurement(context.serialno)
    api = MapApi()

    measurement.report_event("MAP", "app-start")
    app.build()
    app.mainloop()

