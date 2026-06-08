import tkinter
import tkinter.messagebox
from tkinter import messagebox
from tkinter.colorchooser import askcolor
import customtkinter as ctk
import os
import sqlite3
import hashlib
import asyncio
import threading
from bleak import BleakClient
from PIL import Image, ImageTk

# Resolve paths relative to this file so the app works from any working directory.
_HERE = os.path.dirname(os.path.realpath(__file__))
DB_PATH = os.path.join(_HERE, "userdata.db")
print(DB_PATH)

class App(ctk.CTk):
    def __init__(self, user):
        super().__init__()

        # ── Database: load this user's RGB mapping ────────────────────────────
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT rgb_mapping FROM userdata WHERE id = ?", [user])
        output = cur.fetchone()[0].split('#')
        # 53 hex colour strings: notes 0-47, then metronome/normal/fade1/2/3
        self.rgb_mapping = ["#" + output[i] for i in range(1, 54)]
        conn.close()

        # ── Constants ─────────────────────────────────────────────────────────
        self.USER = user
        self.BUTTON_HEIGHT = 40
        self.NOTES = ("A", "A#/Bb", "B", "C", "C#/Db", "D", "D#/Eb", "E", "F", "F#/Gb", "G", "G#/Ab")
        self.NAME_TO_INDEX = {"Home": 0, "RGB map": 1, "Mode": 2, "Bluetooth": 3, "Settings": 4, "Switch User": 5}
        self.HOVER_COLOUR = ("gray70", "gray30")
        self.TEXT_COLOUR = ("gray10", "gray90")
        self.DEVICE_ADDRESS = "F4:12:FA:FA:0E:A9"
        self.CHARACTERISTIC_UUID = "005e1887-1150-43e5-a985-b1b741437ea6"
        self.IMAGE_PATH = os.path.join(_HERE, "assets")

        # ── BLE: persistent async connection on a dedicated background thread ─
        # The asyncio event loop lives entirely on _ble_thread so Tkinter's
        # main thread is never blocked.  Use bluetooth_send() from UI callbacks;
        # it submits coroutines via run_coroutine_threadsafe and returns immediately.
        self._ble_loop = asyncio.new_event_loop()
        self._ble_thread = threading.Thread(target=self._ble_loop.run_forever, daemon=True)
        self._ble_thread.start()
        self._client = None
        self._connected = False

        # ── State ─────────────────────────────────────────────────────────────
        self.current_octave = 1
        self.sel_mode = 0

        # ── Images ────────────────────────────────────────────────────────────
        self.iconpath = ImageTk.PhotoImage(file=os.path.join(self.IMAGE_PATH, "GUI_icon.bmp"))
        self.wm_iconbitmap()
        self.iconphoto(False, self.iconpath)
        self.logo_image = ctk.CTkImage(Image.open(os.path.join(self.IMAGE_PATH, "GUI_icon.png")), size=(26, 26))
        self.top_title_image = ctk.CTkImage(Image.open(os.path.join(self.IMAGE_PATH, "OIP.jpeg")), size=(700, 60))
        self.button_image = ctk.CTkImage(Image.open(os.path.join(self.IMAGE_PATH, "button_image.png")), size=(100, 30))
        self.right_arrow_button_image = ctk.CTkImage(Image.open(os.path.join(self.IMAGE_PATH, "right_arrow.png")), size=(30, 30))
        self.left_arrow_button_image = ctk.CTkImage(Image.open(os.path.join(self.IMAGE_PATH, "right_arrow.png")).rotate(180), size=(30, 30))
        self.ble_connected_image = ctk.CTkImage(Image.open(os.path.join(self.IMAGE_PATH, "connected.jpg")), size=(100, 100))
        self.ble_disconnected_image = ctk.CTkImage(Image.open(os.path.join(self.IMAGE_PATH, "disconnected.jpg")), size=(100, 100))

        # ── Window layout ─────────────────────────────────────────────────────
        self.title("Note lamp GUI")
        self.geometry("1100x580")
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar_frame = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=10)
        ctk.CTkLabel(self.sidebar_frame, text="Side options",
                     font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))

        def _nav_btn(row, label, frame_name):
            btn = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=self.BUTTON_HEIGHT,
                                border_spacing=10, text=label, fg_color="transparent",
                                text_color=self.TEXT_COLOUR, hover_color=self.HOVER_COLOUR,
                                anchor="w", command=lambda: self.select_frame_by_name(frame_name))
            btn.grid(row=row, column=0, sticky="ew")
            return btn

        self.home_button        = _nav_btn(1, "Home",                 "Home")
        self.RGB_button         = _nav_btn(2, "RGB map",              "RGB map")
        self.mode_button        = _nav_btn(3, "Mode selection",       "Mode")
        self.bluetooth_button   = _nav_btn(4, "Bluetooth connection", "Bluetooth")
        self.settings_button    = _nav_btn(5, "Settings",             "Settings")
        self.switch_user_button = _nav_btn(6, "Switch user",          "Switch User")
        self.buttons = [self.home_button, self.RGB_button, self.mode_button,
                        self.bluetooth_button, self.settings_button, self.switch_user_button]

        # ── Central frames ────────────────────────────────────────────────────
        self.home_frame      = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.RGB_frame       = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.mode_frame      = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.bluetooth_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.settings_frame  = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.central_frames  = [self.home_frame, self.RGB_frame, self.mode_frame,
                                self.bluetooth_frame, self.settings_frame]

        # Top title
        self.top_title_frame = ctk.CTkFrame(self, corner_radius=100, bg_color="red", width=1200)
        self.top_title_frame.grid(row=0, column=1, padx=20, pady=10)
        self.top_title = ctk.CTkLabel(self.top_title_frame, text="Top title",
                                      font=ctk.CTkFont(size=36, weight="bold"),
                                      image=self.top_title_image)
        self.top_title.pack()

        # ── Home frame ────────────────────────────────────────────────────────
        self.home_frame.grid_columnconfigure(0, weight=1)
        home_sub = ctk.CTkFrame(self.home_frame, corner_radius=0, fg_color=("light blue", "dark blue"))
        home_sub.grid(row=1, column=0, pady=20, padx=20)
        home_sub.grid_columnconfigure(0, weight=1, minsize=500)
        ctk.CTkLabel(home_sub, text="Welcome", font=ctk.CTkFont(size=20, weight="bold"),
                     fg_color=("grey70", "grey30")).grid(row=0, column=0, padx=20, pady=(20, 10))
        welcome_text = ctk.CTkLabel(home_sub, font=ctk.CTkFont(size=14),
                                    text="This is the home page of the application. On the left there are "
                                         "multiple windows where you can edit, configure, and customise all "
                                         "aspects about the lamp and the GUI.")
        welcome_text.configure(wraplength=400)
        welcome_text.grid(row=1, column=0, padx=20, pady=(20, 10))

        # ── RGB map frame ─────────────────────────────────────────────────────
        self.RGB_frame.grid_columnconfigure(0, weight=1)
        self.RGB_subframe = ctk.CTkFrame(self.RGB_frame, corner_radius=0, fg_color="yellow")
        self.RGB_subframe.grid(row=1, column=0, pady=50, padx=20)
        self.RGB_subframe.grid_columnconfigure(0, weight=1)
        self.RGB_buttons = [
            ctk.CTkButton(self.RGB_subframe, text=self.NOTES[i] + str(self.current_octave),
                          fg_color="red", command=lambda i=i: self.choose_RGB_color(i),
                          width=40, height=40)
            for i in range(12)
        ]
        for i, btn in enumerate(self.RGB_buttons):
            btn.grid(row=0, column=i, padx=5, pady=5)
        self.inc_oc_button = ctk.CTkButton(self.RGB_subframe, fg_color=None, text="-->",
                                           font=("arial", 14, "bold"), width=30,
                                           command=lambda: self.change_octave(1))
        self.inc_oc_button.grid(row=1, column=11, padx=0, pady=15)
        self.dec_oc_button = ctk.CTkButton(self.RGB_subframe, fg_color=None, text="<--",
                                           font=("arial", 14, "bold"), width=30,
                                           command=lambda: self.change_octave(-1))
        self.dec_oc_button.grid(row=1, column=0, padx=0, pady=15)

        # ── Mode frame ────────────────────────────────────────────────────────
        self.mode_frame.grid_columnconfigure(0, weight=1)
        self.mode_subframe = ctk.CTkFrame(self.mode_frame, corner_radius=0, fg_color="blue")
        self.mode_subframe.grid(row=0, column=0, pady=20, padx=20)
        self.mode_subframe.grid_columnconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self.mode_subframe, width=700)
        self.tabview.grid(row=0, column=2, padx=20, pady=20, sticky="nsew")
        self.tabview.add("Note match")
        self.tabview.add("Metronome")
        self.tabview.add("Normal lamp")
        self.tabview.add("Fade pattern")
        self.tabview.tab("Note match").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Metronome").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Normal lamp").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Fade pattern").grid_columnconfigure((0, 1, 2), weight=1)

        # Note match tab
        ctk.CTkLabel(self.tabview.tab("Note match"),
                     text="This mode makes your lamp flash based on the notes it hears in the "
                          "background, using the colours assigned in the RGB map.").grid(
            row=0, column=0, padx=20, pady=20)
        self.note_mode = ctk.CTkButton(self.tabview.tab("Note match"), text="Activate mode",
                                       command=lambda: self.mode(0))
        self.note_mode.grid(row=1, column=0, padx=20, pady=10)

        # Metronome tab
        ctk.CTkLabel(self.tabview.tab("Metronome"),
                     text="This mode makes your lamp flash at a rate set by the slider below.").grid(
            row=0, column=0, padx=20, pady=20)
        self.bpm_slider = ctk.CTkSlider(self.tabview.tab("Metronome"), from_=30, to=220,
                                        command=self.change_bpm)
        self.bpm_slider.set(90)
        self.bpm_slider.grid(row=1, column=0, padx=20, pady=20)
        self.bpm_label = ctk.CTkLabel(self.tabview.tab("Metronome"), text="90 bpm")
        self.bpm_label.grid(row=2, column=0)
        self.colour_metronome_button = ctk.CTkButton(self.tabview.tab("Metronome"),
                                                     text="Pick a colour",
                                                     fg_color=self.rgb_mapping[48],
                                                     command=lambda: self.choose_RGB_color(12))
        self.colour_metronome_button.grid(row=3, column=0, padx=20, pady=10)
        self.metronome_mode = ctk.CTkButton(self.tabview.tab("Metronome"), text="Activate mode",
                                            command=lambda: self.mode(1))
        self.metronome_mode.grid(row=4, column=0, padx=20, pady=10)

        # Normal lamp tab
        ctk.CTkLabel(self.tabview.tab("Normal lamp"),
                     text="This mode sets your lamp to a constant colour.").grid(
            row=0, column=0, padx=20, pady=20)
        self.colour_button = ctk.CTkButton(self.tabview.tab("Normal lamp"), text="Pick a colour",
                                           fg_color=self.rgb_mapping[49],
                                           command=lambda: self.choose_RGB_color(13))
        self.colour_button.grid(row=1, column=0, padx=20, pady=10)
        self.colour_mode = ctk.CTkButton(self.tabview.tab("Normal lamp"), text="Activate mode",
                                         command=lambda: self.mode(2))
        self.colour_mode.grid(row=2, column=0, padx=20, pady=10)

        # Fade pattern tab
        ctk.CTkLabel(self.tabview.tab("Fade pattern"),
                     text="This mode makes your lamp fade across 3 colours picked by you.").grid(
            row=0, column=1, padx=20, pady=20)
        self.fade_colour_button_1 = ctk.CTkButton(self.tabview.tab("Fade pattern"), text="Colour 1",
                                                   fg_color=self.rgb_mapping[50],
                                                   command=lambda: self.choose_RGB_color(14))
        self.fade_colour_button_1.grid(row=1, column=0, padx=20, pady=10)
        self.fade_colour_button_2 = ctk.CTkButton(self.tabview.tab("Fade pattern"), text="Colour 2",
                                                   fg_color=self.rgb_mapping[51],
                                                   command=lambda: self.choose_RGB_color(15))
        self.fade_colour_button_2.grid(row=1, column=1, padx=20, pady=10)
        self.fade_colour_button_3 = ctk.CTkButton(self.tabview.tab("Fade pattern"), text="Colour 3",
                                                   fg_color=self.rgb_mapping[52],
                                                   command=lambda: self.choose_RGB_color(16))
        self.fade_colour_button_3.grid(row=1, column=2, padx=20, pady=10)
        self.fade_reset_button = ctk.CTkButton(self.tabview.tab("Fade pattern"),
                                               text="Reset fade pattern",
                                               command=self.fade_reset)
        self.fade_reset_button.grid(row=2, column=1, padx=20, pady=10)
        self.fade_mode = ctk.CTkButton(self.tabview.tab("Fade pattern"), text="Activate mode",
                                       command=lambda: self.mode(3))
        self.fade_mode.grid(row=3, column=1, padx=20, pady=10)

        self.activate_buttons = [self.note_mode, self.metronome_mode, self.colour_mode, self.fade_mode]
        # Extend RGB_buttons with the 5 special colour buttons (indices 12-16)
        self.RGB_buttons += [self.colour_metronome_button, self.colour_button,
                             self.fade_colour_button_1, self.fade_colour_button_2,
                             self.fade_colour_button_3]

        # ── Bluetooth frame ───────────────────────────────────────────────────
        self.bluetooth_frame.grid_columnconfigure(0, weight=1)
        bluetooth_sub = ctk.CTkFrame(self.bluetooth_frame, corner_radius=0,
                                     fg_color=("light blue", "dark blue"))
        bluetooth_sub.grid(row=1, column=0, pady=20, padx=20)
        bluetooth_sub.grid_columnconfigure(0, weight=1, minsize=500)

        self.bluetooth_status_label = ctk.CTkLabel(bluetooth_sub, text="Disconnected",
                                                   image=self.ble_disconnected_image,
                                                   compound="top",
                                                   font=ctk.CTkFont(size=14))
        self.bluetooth_status_label.grid(row=0, column=0, padx=20, pady=20)
        ctk.CTkButton(bluetooth_sub, text="Connect",
                      command=self.bluetooth_connect).grid(row=1, column=0, padx=20, pady=10)
        ctk.CTkButton(bluetooth_sub, text="Disconnect",
                      command=self.bluetooth_disconnect).grid(row=2, column=0, padx=20, pady=10)
        ctk.CTkLabel(bluetooth_sub,
                     text=f"Device: {self.DEVICE_ADDRESS}").grid(row=3, column=0, padx=20, pady=5)

        # ── Settings frame ────────────────────────────────────────────────────
        self.settings_frame.grid_columnconfigure(0, weight=1)
        settings_sub = ctk.CTkFrame(self.settings_frame, corner_radius=0,
                                    fg_color=("light blue", "dark blue"))
        settings_sub.grid(row=1, column=0)
        settings_sub.grid_columnconfigure((0, 1), weight=1, minsize=350)
        scaling_label = ctk.CTkLabel(settings_sub, text="UI Scaling:")
        scaling_label.grid(row=0, column=0, padx=20, pady=(10, 0))
        scaling_menu = ctk.CTkOptionMenu(scaling_label,
                                         values=["70%", "80%", "90%", "100%", "110%", "120%", "130%", "140%"],
                                         command=self.change_scaling_event)
        scaling_menu.set("100%")
        scaling_menu.grid(padx=10, pady=10)
        appearance_label = ctk.CTkLabel(settings_sub, text="Appearance Mode:", anchor="w")
        appearance_label.grid(row=0, column=1)
        ctk.CTkButton(appearance_label, text="Toggle appearance mode",
                      command=self.toggle_appearance_mode).grid(padx=10, pady=10)

        # ── Initial state ─────────────────────────────────────────────────────
        self.select_frame_by_name("Home")
        self.change_octave(0)

    # ── BLE: async layer ──────────────────────────────────────────────────────

    def _ble_submit(self, coro):
        """Schedule a coroutine on the BLE event loop. Non-blocking."""
        return asyncio.run_coroutine_threadsafe(coro, self._ble_loop)

    async def _ensure_connected(self):
        if self._client is None or not self._client.is_connected:
            self._client = BleakClient(self.DEVICE_ADDRESS,
                                       disconnected_callback=self._on_ble_disconnect)
            await self._client.connect()
            self._connected = True
            self.after(0, lambda: self._update_ble_ui(True))

    async def _send_async(self, cmd: int, val: int):
        try:
            await self._ensure_connected()
            await self._client.write_gatt_char(self.CHARACTERISTIC_UUID,
                                               bytearray([cmd, val]))
        except Exception as e:
            print(f"BLE send error: {e}")
            self._connected = False
            self.after(0, lambda: self._update_ble_ui(False))

    def _on_ble_disconnect(self, client):
        """Called by Bleak from the BLE thread on unexpected disconnection."""
        self._connected = False
        self.after(0, lambda: self._update_ble_ui(False))

    def _update_ble_ui(self, connected: bool):
        """Update the Bluetooth frame status. Must be called on the Tkinter thread."""
        try:
            if connected:
                self.bluetooth_status_label.configure(text="Connected",
                                                      image=self.ble_connected_image)
            else:
                self.bluetooth_status_label.configure(text="Disconnected",
                                                      image=self.ble_disconnected_image)
        except Exception:
            pass  # widget may be destroyed if the window is closing

    def bluetooth_send(self, cmd: int, val: int):
        """Send a 2-byte command to the lamp. Non-blocking; safe to call from UI callbacks."""
        self._ble_submit(self._send_async(cmd, val))

    def bluetooth_connect(self):
        self._ble_submit(self._ensure_connected())

    def bluetooth_disconnect(self):
        async def _do():
            if self._client and self._client.is_connected:
                await self._client.disconnect()
        self._ble_submit(_do())

    # ── UI logic ──────────────────────────────────────────────────────────────

    def update_SQL(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE userdata SET rgb_mapping = ? WHERE id = ?",
                    ["".join(self.rgb_mapping), self.USER])
        conn.commit()
        conn.close()

    def choose_RGB_color(self, button_index=None):
        if button_index is None:
            return
        result = askcolor(title="Choose colour")
        if result[1] is None:
            return  # user cancelled
        hex_colour = result[1]       # "#RRGGBB"
        r = int(hex_colour[1:3], 16)
        g = int(hex_colour[3:5], 16)
        b = int(hex_colour[5:7], 16)
        self.RGB_buttons[button_index].configure(fg_color=hex_colour)

        if button_index < 12:
            # Note button: firmware index = (octave-1)*12 + button_index
            fw_index = (self.current_octave - 1) * 12 + button_index
            self.rgb_mapping[fw_index] = hex_colour
            self.bluetooth_send(fw_index * 3 + 1, r)
            self.bluetooth_send(fw_index * 3 + 2, g)
            self.bluetooth_send(fw_index * 3 + 3, b)
        elif button_index < 17:
            # Special colour button (12=metronome, 13=normal, 14-16=fade 1/2/3)
            fw_index = 36 + button_index  # maps to firmware indices 48-52
            self.rgb_mapping[fw_index] = hex_colour
            self.bluetooth_send(fw_index * 3 + 1, r)
            self.bluetooth_send(fw_index * 3 + 2, g)
            self.bluetooth_send(fw_index * 3 + 3, b)

        self.update_SQL()

    def change_octave(self, val):
        if (self.current_octave < 4 and val > 0) or (self.current_octave > 1 and val < 0) or val == 0:
            self.current_octave += val
            for i in range(12):
                self.RGB_buttons[i].configure(
                    text=self.NOTES[i] + str(self.current_octave),
                    fg_color=self.rgb_mapping[(self.current_octave - 1) * 12 + i]
                )
        self.inc_oc_button.configure(state="disabled" if self.current_octave == 4 else "normal")
        self.dec_oc_button.configure(state="disabled" if self.current_octave == 1 else "normal")

    def change_bpm(self, val):
        self.bpm_label.configure(text=f"{round(val, 1)} bpm")

    def fade_reset(self):
        pass

    def mode(self, tab_index: int):
        """Activate a lamp mode. tab_index matches the order of tabs in the UI."""
        for btn in self.activate_buttons:
            btn.configure(state="normal")
        self.activate_buttons[tab_index].configure(state="disabled")
        self.sel_mode = tab_index

        # GUI tab order:  0=Note match, 1=Metronome, 2=Normal lamp, 3=Fade pattern
        # Firmware modes: 0=Metronome, 1=Note Match, 2=Normal, 3=Fade
        # BLE command:    0xC8=200→mode0, 0xC9=201→mode1, 0xCA=202→mode2, 0xCB=203→mode3
        tab_to_cmd = {0: 0xC9, 1: 0xC8, 2: 0xCA, 3: 0xCB}
        self.bluetooth_send(tab_to_cmd[tab_index], 0)

        if tab_index == 1:  # Metronome — also send current BPM
            bpm = int(self.bpm_slider.get())
            self.bluetooth_send(0xCD, bpm)

    def select_frame_by_name(self, name):
        index = self.NAME_TO_INDEX[name]
        if index == 5:  # Switch User
            global log_in
            log_in = True
            self.on_closing()  # disconnect BLE + stop loop + destroy
            return
        for i, frame in enumerate(self.central_frames):
            frame.grid_forget()
            self.buttons[i].configure(fg_color="transparent")
        self.central_frames[index].grid(row=1, column=1, sticky="nsew")
        self.buttons[index].configure(fg_color=("gray75", "gray25"))
        self.top_title.configure(text=name)

    def change_scaling_event(self, new_scaling):
        if "%" in new_scaling:
            new_scaling = new_scaling.replace("%", "")
        ctk.set_widget_scaling(float(new_scaling) * 0.01)

    def toggle_appearance_mode(self):
        ctk.set_appearance_mode("Dark" if ctk.get_appearance_mode() == "Light" else "Light")

    def on_closing(self):
        self.bluetooth_disconnect()
        self._ble_loop.call_soon_threadsafe(self._ble_loop.stop)
        self.destroy()


# ── Login window ──────────────────────────────────────────────────────────────

class Login(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.conn = sqlite3.connect(DB_PATH)
        self.cur = self.conn.cursor()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.geometry("500x300")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Login frame
        self.frame = ctk.CTkFrame(master=self)
        self.frame.pack(pady=20, padx=60, fill="both", expand=True)
        ctk.CTkLabel(master=self.frame, text="Login System").pack(pady=12, padx=10)
        self.entry1 = ctk.CTkEntry(master=self.frame, placeholder_text="Username")
        self.entry1.pack(pady=12, padx=10)
        self.entry2 = ctk.CTkEntry(master=self.frame, placeholder_text="Password", show="*")
        self.entry2.pack(pady=12, padx=10)
        btn_frame = ctk.CTkFrame(self.frame, corner_radius=0, fg_color="transparent")
        btn_frame.pack(pady=12, padx=20)
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btn_frame, text="Login",    command=self.login).grid(row=0, column=0, pady=12, padx=20)
        ctk.CTkButton(btn_frame, text="Add user", command=lambda: self.new_user(2)).grid(row=0, column=1, pady=12, padx=20)

        # Add-user frame
        self.user_frame = ctk.CTkFrame(master=self)
        self.user_frame.pack(pady=20, padx=60, fill="both", expand=True)
        ctk.CTkLabel(master=self.user_frame, text="Add user").pack(pady=12, padx=10)
        self.user_entry1 = ctk.CTkEntry(master=self.user_frame, placeholder_text="Username")
        self.user_entry1.pack(pady=12, padx=10)
        self.user_entry2 = ctk.CTkEntry(master=self.user_frame, placeholder_text="Password", show="*")
        self.user_entry2.pack(pady=12, padx=10)
        ubtn_frame = ctk.CTkFrame(self.user_frame, corner_radius=0, fg_color="transparent")
        ubtn_frame.pack(pady=12, padx=20)
        ubtn_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(ubtn_frame, text="Back",     fg_color="#C3862F", hover_color="#7D571F",
                      command=lambda: self.new_user(1)).grid(row=0, column=0, pady=12, padx=20)
        ctk.CTkButton(ubtn_frame, text="New user", fg_color="#C3862F", hover_color="#7D571F",
                      command=lambda: self.new_user(0)).grid(row=0, column=1, pady=12, padx=20)

        self.new_user(1)  # show login frame first

    def login(self):
        username = self.entry1.get()
        password = self.entry2.get()
        if not username or not password or " " in username or " " in password:
            messagebox.showerror("Error", "Enter a valid username and password.")
            return
        self.cur.execute("SELECT id, username, password FROM userdata WHERE username=?", [username])
        result = self.cur.fetchone()
        if result is None:
            messagebox.showerror("Error", "Incorrect username.")
            return
        if hashlib.sha256(password.encode()).hexdigest() != result[2]:
            messagebox.showerror("Error", "Incorrect password.")
            return
        global logged_in, log_in, user
        user = result[0]
        logged_in = True
        log_in = False
        self.destroy()

    def new_user(self, val):
        if val == 0:
            username = self.user_entry1.get()
            password = self.user_entry2.get()
            if not username or not password or " " in username or " " in password:
                messagebox.showerror("Error", "Enter a valid username and password.")
            else:
                self.cur.execute("SELECT username FROM userdata WHERE username=?", [username])
                if self.cur.fetchone() is not None:
                    messagebox.showerror("Error", "Username already exists.")
                else:
                    h = hashlib.sha256(password.encode()).hexdigest()
                    blank_rgb = "#000000" * 53
                    self.cur.execute("INSERT INTO userdata (username, password, rgb_mapping) VALUES (?,?,?)",
                                     (username, h, blank_rgb))
                    self.conn.commit()
                    messagebox.showinfo("Success", "New user created.")
            self.user_frame.pack_forget()
            self.frame.pack(pady=20, padx=60, fill="both", expand=True)
        elif val == 1:
            self.user_frame.pack_forget()
            self.frame.pack(pady=20, padx=60, fill="both", expand=True)
        elif val == 2:
            self.frame.pack_forget()
            self.user_frame.pack(pady=20, padx=60, fill="both", expand=True)

    def on_closing(self):
        self.conn.close()
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

logged_in = False
log_in = True
user = 0

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    while log_in:
        login = Login()
        login.mainloop()
        log_in = False
        if logged_in:
            logged_in = False
            app = App(user)
            app.mainloop()
    print("Finished")
