#!/usr/bin/python3
import os
import configparser
from datetime import datetime
from pathlib import Path
import socket
import json
import threading
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import pygame
import collections
import gettext
from importlib.metadata import version, PackageNotFoundError
import sys
import tomllib  # Falls Python < 3.11, dann: import toml
from pathlib import Path
import time


def get_version():
    """Liest die Version aus pyproject.toml"""

    # Prüfen, ob Programm gebündelt ist (PyInstaller)
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)  # Temp-Verzeichnis von PyInstaller
    else:
        base_path = Path(__file__).parent.parent  # Standard-Pfad im normalen Python-Lauf
    
    toml_path = base_path / "pyproject.toml"

    if toml_path.exists():
        with toml_path.open("rb") as f:
            config = tomllib.load(f)
        return config.get("project", {}).get("version", "0.1.0")  # <== Hier geändert!
    
    return "unknown"  # Standardwert, falls Datei nicht gefunden wird

__version__ = get_version()
print(f"Programmversion: {__version__}")

if __version__ == "unknown":
    try:
        __version__ = version("MeshCom-Client")
    except PackageNotFoundError:
        __version__ = "unknown"

print(f"MeshCom-Client Version: {__version__}")


last_sent_time = 0  # Speichert die Zeit der letzten Nachricht
SEND_DELAY = 40  # Wartezeit zum Senden neuer Nachrichten in Sekunden

# Wir speichern die letzten 20 IDs in einer deque
received_ids = collections.deque(maxlen=5)  # maxlen sorgt dafür, dass nur die letzten 5 IDs gespeichert werden

# Server-Konfiguration
UDP_IP_ADDRESS = "0.0.0.0"
UDP_PORT_NO = 1799

DEFAULT_DST = "*"  # Standardziel für Nachrichten (Broadcast)
DESTINATION_PORT = 1799  # Ziel-Port anpassen
MAX_MESSAGE_LENGTH = 149  # Maximale Länge der Nachricht

# Einstellungen
current_dir = Path(__file__).parent
CONFIG_FILE = Path(__file__).parent / 'settings.ini'
config = configparser.ConfigParser()

# Chatlog
CHATLOG_FILE = Path(__file__).parent / 'chatlog.json'

# Audio-Dateien
NEW_MESSAGE = Path(__file__).parent / "sounds" / "new_message.wav"

CALLSIGN_ALERT = Path(__file__).parent / "sounds" / "alert.wav"

OWN_CALLSIGN = Path(__file__).parent / "sounds" / "mycall.wav"


# Dictionary zur Verwaltung der Tabs
tab_frames = {}
open_tabs = set()
tab_highlighted = set()  # Set für Tabs, die hervorgehoben werden sollen


#Set für Watchlist
watchlist = set()

# Dictionary zum Speichern der Text-Widgets für verschiedene Rufzeichen-Tabs
text_areas = {}

language = "de" # Standardsprache

volume = 0.5  # Standardlautstärke (50%)

# Ziel-IP aus Einstellungen laden oder Standardwert setzen
DESTINATION_IP = "192.168.178.28"

# Eigenes Rufzeichen aus Einstellungen laden oder Standardwert setzen
MYCALL = "DG9VH-99"


class SettingsDialog(tk.Toplevel):
    def __init__(self, master, initial_volume, initial_new_message, initial_callsign_alert, initial_owncall_alert, save_callback):
        super().__init__(master)
        self.title(_("Einstellungen"))
        self.geometry("700x450")
        self.resizable(False, False)

        self.save_callback = save_callback

        # Lautstärke-Label
        tk.Label(self, text=_("Lautstärke (0.0 bis 1.0):")).pack(pady=10)

        # Schieberegler für Lautstärke
        self.volume_slider = tk.Scale(
            self,
            from_=0.0,
            to=1.0,
            resolution=0.01,
            orient="horizontal",
            length=250
        )
        self.volume_slider.set(initial_volume)
        self.volume_slider.pack(pady=10)

        #tk.Label(self, text=_("Neue Nachricht:")).pack(pady=10)        
        self.new_message_label = tk.Label(self, text = _("Neue Nachricht:") + " " + initial_new_message, width=200)
        self.new_message_label.pack(pady=10)
        ttk.Button(self, text=_("Datei wählen"), command = self.choose_new_message_file).pack(pady=10)
        
        #tk.Label(self, text=_("Watchlist-Hinweis:")).pack(pady=10)
        self.callsign_alert_label = tk.Label(self, text = _("Watchlist-Hinweis:") + " " + initial_callsign_alert, width=200)
        self.callsign_alert_label.pack(pady=10)
        ttk.Button(self, text=_("Datei wählen"), command = self.choose_callsign_alert_file).pack(pady=10)
        
        #tk.Label(self, text=_("Eigenes Rufzeichen-Hinweis:")).pack(pady=10)
        self.owncall_alert_label = tk.Label(self, text = _("Eigenes Rufzeichen-Hinweis:") + " " + initial_owncall_alert, width=200)
        self.owncall_alert_label.pack(pady=10)
        ttk.Button(self, text=_("Datei wählen"), command = self.choose_owncall_alert_file).pack(pady=10)

        
        # Speichern-Button
        ttk.Button(self, text=_("Speichern"), command = self.save_settings).pack(pady=10)


    def choose_new_message_file(self):
        global NEW_MESSAGE
        """Öffnet einen Datei-Dialog und setzt die Variable auf den ausgewählten Dateinamen."""
        NEW_MESSAGE = filedialog.askopenfilename(filetypes=[("WAV-Dateien", "*.wav")])
        
        self.new_message_label.config(text = _("Neue Nachricht:") + " " + NEW_MESSAGE)


    def choose_callsign_alert_file(self):
        global CALLSIGN_ALERT
        """Öffnet einen Datei-Dialog und setzt die Variable auf den ausgewählten Dateinamen."""
        CALLSIGN_ALERT = filedialog.askopenfilename(filetypes=[("WAV-Dateien", "*.wav")])
        
        self.callsign_alert_label.config(text = _("Watchlist-Hinweis:") + " " + CALLSIGN_ALERT)


    def choose_owncall_alert_file(self):
        global OWN_CALLSIGN
        """Öffnet einen Datei-Dialog und setzt die Variable auf den ausgewählten Dateinamen."""
        OWN_CALLSIGN = filedialog.askopenfilename(filetypes=[("WAV-Dateien", "*.wav")])
        
        self.owncall_alert_label.config(text = _("Eigenes Rufzeichen-Hinweis:") + " " + OWN_CALLSIGN)


    def save_settings(self):
        # Lautstärke speichern und zurückgeben
        volume = self.volume_slider.get()
        self.save_callback(volume, NEW_MESSAGE, CALLSIGN_ALERT, OWN_CALLSIGN)
        self.destroy()
        

class WatchlistDialog(tk.Toplevel):
    global watchlist
    def __init__(self, master, initial_volume, save_callback):
        super().__init__(master)
        self.title(_("Einstellungen"))
        self.geometry("600x400")
        self.resizable(False, False)

        self.save_callback = save_callback

        tk.Label(self, text=_("Rufzeichen hinzufügen (ohne -SSID):")).grid(row=0, column=0, sticky="w")

        self.entry_callsign = tk.Entry(self)
        self.entry_callsign.grid(row=0, column=1, padx=5)

        self.btn_add = tk.Button(self, text=_("Hinzufügen"), command=self.add_callsign)
        self.btn_add.grid(row=0, column=2, padx=5)

        self.listbox = tk.Listbox(self, height=10, width=30)
        self.listbox.grid(row=1, column=0, columnspan=2, pady=5)

        self.btn_remove = tk.Button(self, text=_("Löschen"), command=self.remove_callsign)
        self.btn_remove.grid(row=1, column=2, padx=5)

        # Watchlist laden
        for call in watchlist:
            self.listbox.insert(tk.END, call)


    def save_watchlist(self):
        """Speichert die aktuelle Watchlist in die Settings"""
        save_settings();
        
        
    def add_callsign(self):
        """Fügt ein neues Rufzeichen zur Watchlist hinzu."""
        callsign = self.entry_callsign.get().strip().upper()
        if callsign and callsign not in watchlist:
            watchlist.add(callsign)
            self.listbox.insert(tk.END, callsign)
            self.entry_callsign.delete(0, tk.END)
            self.save_watchlist()
        elif callsign in watchlist:
            messagebox.showwarning(_("Warnung"), ("{callsign} ist bereits in der Watchlist.").format(callsign=callsign))


    def remove_callsign(self):
        """Löscht das ausgewählte Rufzeichen aus der Watchlist."""
        selected = self.listbox.curselection()
        if selected:
            callsign = self.listbox.get(selected[0])
            watchlist.remove(callsign)
            self.listbox.delete(selected[0])
            self.save_watchlist()
            
        
    def save_settings(self):
        # Watchlist speichern und zurückgeben
        self.save_callback(watchlist)
        self.destroy()


def load_settings():
    """Lädt Einstellungen aus der INI-Datei."""
    global DESTINATION_IP, MYCALL, volume, language, watchlist, NEW_MESSAGE, CALLSIGN_ALERT, OWN_CALLSIGN, SEND_DELAY, open_tabs
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        DESTINATION_IP = config.get("Settings", "DestinationIP", fallback=DESTINATION_IP)
        MYCALL = config.get("Settings", "MyCall", fallback=MYCALL)
        volume = config.getfloat("Settings", "Volume", fallback=0.5)
        SEND_DELAY = config.getint("Settings", "SendDelay", fallback=40)
        if SEND_DELAY < 10:
            SEND_DELAY = 10
        if SEND_DELAY > 40:
            SEND_DELAY = 40
        language = config.get("GUI", "Language", fallback="de")
        watchlist = set(config.get("watchlist", "callsigns", fallback="").split(","))
        open_tabs = sorted(set(config.get("tablist", "tabs", fallback="").split(",")))
        
        NEW_MESSAGE = config.get("Audio", "new_message", fallback=NEW_MESSAGE)
        CALLSIGN_ALERT = config.get("Audio", "callsign_alert", fallback=CALLSIGN_ALERT)
        OWN_CALLSIGN = config.get("Audio", "own_callsign", fallback=OWN_CALLSIGN)


def reopen_tabs():
    global open_tabs
    for tab in open_tabs:
        create_tab(tab)


def save_settings():
    """Speichert Einstellungen in die INI-Datei."""
    config["GUI"] = {
        "language": language,
    }
    config["Settings"] = {
        "DestinationIP": DESTINATION_IP,
        "MYCALL": MYCALL,
        "Volume": volume,
        "SendDelay": SEND_DELAY,
    }
    config["Audio"] = {
        "new_message": NEW_MESSAGE,
        "callsign_alert": CALLSIGN_ALERT,
        "own_callsign": OWN_CALLSIGN,
    }
    config["watchlist"] = {"callsigns": ",".join(watchlist)}
    config["tablist"] = {"tabs": ",".join(tab_frames)}
    
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)


def open_settings_dialog():
    def save_audio_settings(new_volume, new_newmessage, new_callsign_alert, new_own_callsign):
        global volume, NEW_MESSAGE
        volume = new_volume
        NEW_MESSAGE = new_newmessage
        CALLSIGN_ALERT = new_callsign_alert
        OWN_CALLSIGN = new_own_callsign
        save_settings()
        print(_("Lautstärke gespeichert: {volume}").format(volume=volume))
        print(_("Neue Nachricht-Hinweis: {NEW_MESSAGE}").format(NEW_MESSAGE=NEW_MESSAGE))
        print(_("Rufzeichen-Hinweis: {CALLSIGN_ALERT}").format(CALLSIGN_ALERT=CALLSIGN_ALERT))
        print(_("Eigenes-Rufzeichen-Hinweis: {OWN_CALLSIGN}").format(OWN_CALLSIGN=OWN_CALLSIGN))

    SettingsDialog(root, volume, NEW_MESSAGE, CALLSIGN_ALERT, OWN_CALLSIGN, save_audio_settings)


def open_watchlist_dialog():
    def save_watchlist(new_watchlist):
        global watchlist
        watchlist = new_watchlist
        save_settings()
        print(_(f"Watchlist gespeichert"))

    WatchlistDialog(root, watchlist, save_watchlist)
    

def save_chatlog(chat_data):
    with open(CHATLOG_FILE, "w") as f:
        print(_("Speichere Chatverlauf"))
        json.dump(chat_data, f, indent=4)
        print(_("Speichern beendet"))


# Funktion zum Löschen des Chatverlaufs
def delete_chat(rufzeichen, text_widget, tab_control, tab):
    global chat_storage

    if rufzeichen in chat_storage:
        # Bestätigung einholen
        if messagebox.askyesno(_("Chat löschen"), _("Soll der Chatverlauf für {rufzeichen} wirklich gelöscht werden?").format(rufzeichen=rufzeichen)):
            # Entferne den Chat aus der Datei
            del chat_storage[rufzeichen]
            save_chatlog(chat_storage)

            # Entferne den Chat aus der GUI (Textfeld leeren)
            text_widget.delete("1.0", tk.END)

            # Optional: Tab schließen
            tab_control.forget(tab)

            messagebox.showinfo(_("Gelöscht"), _("Chatverlauf für {rufzeichen} wurde gelöscht.").format(rufzeichen=rufzeichen))
    else:
        messagebox.showwarning(_("Nicht gefunden"), _("Kein Chatverlauf für {rufzeichen} vorhanden.").format(rufzeichen=rufzeichen))


def load_chatlog():
    if os.path.exists(CHATLOG_FILE):
        with open(CHATLOG_FILE, "r") as f:
            return json.load(f)
    return {}


def play_sound_with_volume(file_path, volume=1.0):
    """
    Spielt eine Sounddatei mit einstellbarer Lautstärke ab.
    :param file_path: Pfad zur WAV-Datei.
    :param volume: Lautstärke (zwischen 0.0 und 1.0).
    """
    try:
        pygame.mixer.init()
        sound = pygame.mixer.Sound(file_path)
        sound.set_volume(volume)
        sound.play()
        
        while pygame.mixer.get_busy():
            pygame.time.delay(100)
            
    except Exception as e:
        print(_("Fehler beim Abspielen der Sounddatei: {e}").format(e=e))
        

def receive_messages():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((UDP_IP_ADDRESS, UDP_PORT_NO))
    print(_("Server gestarted, hört auf {UDP_IP_ADDRESS}:{UDP_PORT_NO}").format(UDP_IP_ADDRESS=UDP_IP_ADDRESS, UDP_PORT_NO=UDP_PORT_NO))

    while True:
        try:
            data, addr = server_sock.recvfrom(1024)
            decoded_data = data.decode('utf-8')
            print(_("Daten empfangen von {addr}: {decoded_data}").format(addr=addr, decoded_data=decoded_data))

            json_data = json.loads(decoded_data)
            display_message(json_data)
        except Exception as e:
            print(_("Es ist ein Fehler aufgetreten: {e}").format(e=e))


def display_message(message):
    src_call = message.get('src', 'Unknown')
    dst_call = message.get('dst', 'Unknown')
            
    msg_text = message.get('msg', '')
    msg_text = msg_text.replace('"',"'")
    message_id = message.get("msg_id", '')
    msg_tag = ""
    confirmed = False  # Standardmäßig nicht bestätigt
    
    if dst_call == MYCALL:
        dst_call = src_call
        if  msg_text[-4] == "{":
            msg_tag = msg_text[-3:]
            msg_text = msg_text[:-4]
        
        if msg_text.find("ack") > 0:
                msg_text = msg_text[msg_text.find("ack"):]
                if msg_text[0:3] == "ack" and len(msg_text) == 6:
                    msg_tag = msg_text [-3:]
                    confirmed = True  # Nachricht ist bestätigt
                    if dst_call.find(',') > 0:
                        dst_call = dst_call[:dst_call.find(',')]
                    tab_frames[dst_call].tag_config(msg_tag, foreground="green")  # Ändere die Farbe
                    update_message(dst_call, msg_tag)
                    return
            
    if src_call == MYCALL and msg_text[-4] == "{" and not (isinstance(dst_call, int) or dst_call =="*"):
        msg_tag = msg_text[-3:]
        msg_text = msg_text[:-4] 
    
    if dst_call.find(',') > 0:
        dst_call = dst_call[:dst_call.find(',')]

    if message_id == '':
        return
    
    if message_id in received_ids:
        print(_("Nachricht mit ID {message_id} bereits empfangen und verarbeitet.").format(message_id=message_id))
        return  # Nachricht wird ignoriert, da sie bereits verarbeitet wurde
    
    if msg_text == '':
        return

    if "{CET}"in msg_text:
        net_time.config(state="normal")
        net_time.delete(0, tk.END)
        net_time.insert(0, msg_text[5:])
        net_time.config(state="disabled")
        return
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if dst_call not in tab_frames:
        create_tab(dst_call)

    display_text = f"{timestamp} - {src_call}: {msg_text}\n"
    start_index = tab_frames[dst_call].index("end-1c linestart")
    tab_frames[dst_call].config(state=tk.NORMAL)
    tab_frames[dst_call].insert(tk.END, display_text)
    tab_frames[dst_call].tag_add(msg_tag, start_index, f"{start_index} lineend")
    tab_frames[dst_call].tag_config(start_index, foreground="black")
    tab_frames[dst_call].config(state=tk.DISABLED)
    tab_frames[dst_call].yview(tk.END)
    
    add_message(dst_call, display_text, msg_tag, confirmed)
    
    callsign = extract_callsign(src_call)
    if callsign in watchlist:
        print(_("ALERT: {callsign} erkannt!").format(callsign=callsign))
        play_sound_with_volume(CALLSIGN_ALERT, volume)
    elif src_call == MYCALL:
        print(_("ALERT: Eigenes Rufzeichen").format(callsign=callsign))
        play_sound_with_volume(OWN_CALLSIGN, volume)
    elif src_call != "You":
        print(_("ALERT: Normale Nachricht").format(callsign=callsign))
        play_sound_with_volume(NEW_MESSAGE, volume)

    # Tab hervorheben
    highlight_tab(dst_call)
    # Nach der Verarbeitung die ID zur deque hinzufügen
    received_ids.append(message_id)


def add_message(call, message, msg_tag, confirmed=False):
    message_data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "message": message.strip(),
        "msg_tag": msg_tag,
        "confirmed": confirmed
    }
    
    if call not in chat_storage:
        chat_storage[call] = []
    chat_storage[call].append(message_data)
    save_chatlog(chat_storage)  # Speichert die Chats direkt
    
    
def update_message(call, msg_tag):
    for entry in chat_storage[call]:
        if entry.get("msg_tag") == msg_tag:
            entry["confirmed"] = True
        
    save_chatlog(chat_storage)  # Speichert die Chats direkt


def update_timer():
    remaining_time = max(0, int(SEND_DELAY - (time.time() - last_sent_time)))
    
    if remaining_time > 0:
        timer_label.config(text=f"{remaining_time}s")
        root.after(1000, update_timer)  # Aktualisiert jede Sekunde
    else:
        timer_label.config(text="Bereit zum Senden")
        send_button.config(state=tk.NORMAL)  # Button wieder aktivieren


def send_message(event=None):
    global last_sent_time
        
    msg_text = message_entry.get()
    msg_text = msg_text.replace('"',"'")
    
    dst_call = dst_entry.get() or DEFAULT_DST

    if not msg_text.strip():
        return


    current_time = time.time()
    
    if current_time - last_sent_time < SEND_DELAY:
        return  
    
    last_sent_time = current_time
    send_button.config(state=tk.DISABLED)  # Button deaktivieren
    update_timer()  # Countdown aktualisieren
    
    message = {
        "type": "msg",
        "dst": dst_call,
        "msg": msg_text
    }

    try:
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        encoded_message = json.dumps(message, ensure_ascii=False).encode('utf-8')
        client_sock.sendto(encoded_message, (DESTINATION_IP, DESTINATION_PORT))
        display_message({"src": "You", "dst": dst_call, "msg": msg_text})
    except Exception as e:
        print(_("Fehler beim Senden: {e}").format(e=e))
    finally:
        client_sock.close()
        message_entry.delete(0, tk.END)


def validate_length(new_text):
    """Validiert die Länge der Eingabe."""
    global characters_left
    chars_left = MAX_MESSAGE_LENGTH - len(new_text)
    characters_left.config(text = str(chars_left))
    return len(new_text) <= MAX_MESSAGE_LENGTH
    

def create_tab(dst_call):
    global text_areas
    tab_frame = ttk.Frame(tab_control)
    tab_control.add(tab_frame, text=dst_call)

    # Titel und Schließen-Button
    tab_header = tk.Frame(tab_frame)
    tab_header.pack(side=tk.TOP, fill="x")

    title_label = tk.Label(tab_header, text=_(f"Ziel:") + " " + dst_call, anchor="w")
    title_label.bind("<Button-1>", reset_tab_highlight)
    title_label.pack(side=tk.LEFT, padx=5)

    close_button = tk.Button(tab_header, text="X", command=lambda: close_tab(dst_call, tab_frame), width=2)
    close_button.pack(side=tk.RIGHT, padx=5)
    
    # Button zum Löschen des Chats
    delete_button = tk.Button(tab_header, text=_("Chat löschen"), command=lambda: delete_chat(dst_call, text_area, tab_control, tab_frame))
    delete_button.pack(side=tk.RIGHT, padx=5)


    # Textfeld
    text_area = tk.Text(tab_frame, wrap=tk.WORD, state=tk.DISABLED, height=20, width=60)
    text_area.bind("<ButtonRelease-1>", lambda event, call=dst_call: on_message_click(event, call))
    text_area.pack(side=tk.LEFT, expand=1, fill="both", padx=10, pady=10)
    
    # Speichern des Widgets im Dictionary
    text_areas[dst_call] = text_area

    scrollbar = tk.Scrollbar(tab_frame, orient=tk.VERTICAL, command=text_area.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text_area.config(yscrollcommand=scrollbar.set)
    
    tab_frames[dst_call] = text_area
    if dst_call in chat_storage:
        print(_("Chat-Historie wiederherstellen"))
        for msg in chat_storage[dst_call]:
            confirmed = False
            try:
                if msg['confirmed']:
                    confirmed = msg['confirmed']
                msg_text = msg['message']
                msg_tag = msg_text
                start_index = tab_frames[dst_call].index("end-1c linestart")
                tab_frames[dst_call].config(state=tk.NORMAL)
                tab_frames[dst_call].insert(tk.END, msg_text + "\n") # Chatverlauf in das Text-Widget einfügen
                tab_frames[dst_call].tag_add(msg_tag, start_index, f"{start_index} lineend")

                if confirmed:
                    tab_frames[dst_call].tag_config(msg_tag, foreground="green")  # Ändere die Farbe               
                tab_frames[dst_call].config(state=tk.DISABLED)
                tab_frames[dst_call].yview(tk.END)
            except:
                # Altes Chatlog-Format
                tab_frames[dst_call].config(state=tk.NORMAL)
                tab_frames[dst_call].insert(tk.END, msg) # Chatverlauf in das Text-Widget einfügen
                tab_frames[dst_call].config(state=tk.DISABLED)
                tab_frames[dst_call].yview(tk.END)
    save_settings()

def close_tab(dst_call, tab_frame):
    global chat_storage
    save_chatlog(chat_storage) 
    if dst_call in tab_frames:
        del tab_frames[dst_call]
    tab_control.forget(tab_frame)
    save_settings()


def highlight_tab(dst_call):
    """Hervorheben des Tabs, wenn eine neue Nachricht eingegangen ist."""
    for i in range(tab_control.index("end")):
        if tab_control.tab(i, "text").startswith(dst_call):
            tab_control.tab(i, text=f"{dst_call} (neu)")
            tab_highlighted.add(dst_call)
            break


def reset_tab_highlight(event):
    """Zurücksetzen der Markierung, wenn der Tab geöffnet wird."""
    current_tab = tab_control.index("current")
    dst_call = tab_control.tab(current_tab, "text").replace(" (neu)", "")
    if dst_call in tab_highlighted:
        tab_control.tab(current_tab, text=dst_call)
        tab_highlighted.remove(dst_call)
    dst_entry.delete(0, tk.END)
    dst_entry.insert(0, dst_call)


def configure_destination_ip():
    """Dialog zur Konfiguration der Ziel-IP-Adresse."""
    global DESTINATION_IP
    new_ip = simpledialog.askstring(_("Node-IP konfigurieren"), _("Geben Sie die neue Node-IP-Adresse ein:"), initialvalue=DESTINATION_IP)
    if new_ip:
        DESTINATION_IP = new_ip
        save_settings()
        messagebox.showinfo(_("Einstellung gespeichert"), _("Neue Node-IP: {DESTINATION_IP}").format(DESTINATION_IP=DESTINATION_IP))


def configure_mycall():
    """Dialog zur Konfiguration des eigenen Rufzeichens."""
    global MYCALL
    new_mycall = simpledialog.askstring(_("Eigenes Rufzeichen konfigurieren"), _("Geben Sie das eigene Rufzeichen mit SSID ein:"), initialvalue=MYCALL)
    if new_mycall:
        MYCALL = new_mycall
        save_settings()
        messagebox.showinfo(_("Einstellung gespeichert"), _("Neues Rufzeichen: {MYCALL}").format(MYCALL=MYCALL))


def configure_senddelay():
    """Dialog zur Konfiguration der Wartezeit."""
    global SEND_DELAY
    new_send_delay = int(simpledialog.askstring(_("Wartezeit konfigurieren"), _("Geben Sie die neue Wartezeit in Sekundn ein (10 ... 40):"), initialvalue=SEND_DELAY))
    if new_send_delay < 10:
        messagebox.showinfo(_("Einstellung korrigieren"), _("Neue Wartezeit: {new_send_delay} ist zu kurz. Bitte mindestens 10 eingeben!").format(new_send_delay=new_send_delay))
        configure_senddelay()
        return
    if new_send_delay > 40:
        messagebox.showinfo(_("Einstellung korrigieren"), _("Neue Wartezeit: {new_send_delay} ist zu lang. Bitte maximal 40 eingeben!").format(new_send_delay=new_send_delay))
        configure_senddelay()
        return
    if new_send_delay:
        SEND_DELAY = new_send_delay
        save_settings()
        messagebox.showinfo(_("Einstellung gespeichert"), _("Neue Wartezeit: {SEND_DELAY}").format(SEND_DELAY=SEND_DELAY))


def set_language(lang):
    """Setzt die Sprache in der Config-Datei und gibt eine Meldung aus."""
    global language
    language = lang
    save_settings()
    messagebox.showinfo(_("Sprache geändert"), _("Die Sprache wurde geändert.\nBitte starten Sie das Programm neu."))


def extract_callsign(src):
    """Extrahiert das Basisrufzeichen ohne SSID aus dem src-Feld."""
    return src.split("-")[0]  # Trenne bei '-' und nimm den ersten Teil


# Lade Rufzeichen aus JSON-Datei
def load_rufzeichen():
    try:
        with open(CHATLOG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return list(data.keys())  # Holt alle Rufzeichen als Liste
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def on_message_click(event, dst_call):
    """Wird aufgerufen, wenn eine Nachricht in der TextArea angeklickt wird"""
    global message_entry
    try:
        text_widget = text_areas.get(dst_call)
        if not text_widget:
            return  # Falls kein Text-Widget gefunden wird

        # Mausposition bestimmen
        index = text_widget.index(f"@{event.x},{event.y}")

        # Zeile holen
        line_start = f"{index.split('.')[0]}.0"
        line_end = f"{index.split('.')[0]}.end"
        message_text = text_widget.get(line_start, line_end).strip()

        # Nachricht parsen: Rufzeichen extrahieren
        parts = message_text.split(" - ")
        if len(parts) > 1:
            sender_info = parts[1].split(":")[0]  # Teil vor dem ersten Doppelpunkt nehmen
            sender_callsign = sender_info.split(",")[0]  # Erstes Rufzeichen extrahieren
            
            # Rufzeichen in die Eingabebox setzen
            message_entry.delete(0, tk.END)
            message_entry.insert(0, f"{sender_callsign}: ")
    except Exception as e:
        print(f"Fehler beim Parsen der Nachricht: {e}")

    
def show_help():
    """Hilfe anzeigen."""
    messagebox.showinfo(_("Hilfe"), _("Dieses Programm ermöglicht den Empfang und das Senden von Nachrichten über das Meshcom-Netzwerk, indem via UDP eine Verbindung zum Node hergestellt wird. Zur Nutzung mit dem Node ist hier vorher auf dem Node mit --extudpip <ip-adresse des Rechners> sowie --extudp on die Datenübertragung zu aktivieren und über die Einstellungen hier die IP-Adresse des Nodes anzugeben."))


def show_about():
    global __version__
    """Über-Dialog anzeigen."""
    messagebox.showinfo(_("Über"), _("MeshCom Client\nVersion {__version__}\nEntwickelt von DG9VH").format(__version__=__version__))


def on_closing():
    save_chatlog(chat_storage)  # Speichert alle offenen Chats
    root.destroy()  # Schließt das Tkinter-Fenster

def main():
    global root, tab_control, chat_storage, dst_entry, message_entry, net_time, characters_left, timer_label, send_button
    # GUI-Setup
    root = tk.Tk()
    root.title(f"MeshCom Client {__version__} by DG9VH")
    root.geometry("950x400")  # Fenstergröße auf 950x400 setzen
    root.protocol("WM_DELETE_WINDOW", on_closing)  # Fängt das Schließen ab

    load_settings()

    appname = 'MeshCom-Client'
    localedir = current_dir / "locales"

    # initialisiere Gettext
    en_i18n = gettext.translation(appname, localedir, fallback=True, languages=[language])
    en_i18n.install()

    chat_storage = load_chatlog()  # Lädt vorhandene Chatlogs beim Programmstart

    # Menüleiste
    menu_bar = tk.Menu(root)
    root.config(menu=menu_bar)

    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label=_("Beenden"), command=root.quit)
    menu_bar.add_cascade(label=_("Datei"), menu=file_menu)

    settings_menu = tk.Menu(menu_bar, tearoff=0)
    settings_menu.add_command(label=_("Node-IP konfigurieren"), command=configure_destination_ip)
    settings_menu.add_command(label=_("Eigenes Rufzeichen"), command=configure_mycall)
    settings_menu.add_command(label=_("Wartezeit"), command=configure_senddelay)
    settings_menu.add_command(label=_("Watchlist"), command=open_watchlist_dialog)
    settings_menu.add_command(label=_("Audioeinstellungen"), command=open_settings_dialog)
    # Untermenü „Sprache“ hinzufügen
    language_menu = tk.Menu(settings_menu, tearoff=0)
    settings_menu.add_cascade(label=_("Sprache"), menu=language_menu)
    # Sprachoptionen hinzufügen
    language_menu.add_command(label="Deutsch", command=lambda: set_language("de"))
    language_menu.add_command(label="English", command=lambda: set_language("en"))

    menu_bar.add_cascade(label=_("Einstellungen"), menu=settings_menu)

    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(label=_("Hilfe"), command=show_help)
    help_menu.add_command(label=_("Über"), command=show_about)
    menu_bar.add_cascade(label=_("Hilfe"), menu=help_menu)

    tab_control = ttk.Notebook(root)
    tab_control.bind("<<NotebookTabChanged>>", reset_tab_highlight)

    input_frame = tk.Frame(root)
    input_frame.pack(fill="x", padx=10, pady=5)

    tk.Label(input_frame, text=_("Nachricht:")).grid(row=0, column=0, padx=5, pady=5, sticky="e")

    vcmd = root.register(validate_length)  # Validation-Command registrieren
    message_entry = tk.Entry(input_frame, width=40, validate="key", validatecommand=(vcmd, "%P"))
    message_entry.grid(row=0, column=1, columnspan=3, padx=5, pady=5)
    message_entry.bind("<Return>", send_message) 
    
    tk.Label(input_frame, text=_("Wartezeit:")).grid(row=1, column=0, padx=5, pady=5, sticky="e")
    timer_label = tk.Label(input_frame, text="0s")
    timer_label.grid(row=1, column=1, padx=5, pady=5, sticky="w")
    
    tk.Label(input_frame, text=_("Zeichen übrig:")).grid(row=1, column=2, padx=5, pady=5, sticky="e")
    characters_left = tk.Label(input_frame, text="149")
    characters_left.grid(row=1, column=3, padx=5, pady=5, sticky="w")

    tk.Label(input_frame, text=_("Ziel:")).grid(row=2, column=0, padx=5, pady=5, sticky="e")
    dst_entry = tk.Entry(input_frame, width=20)
    dst_entry.insert(0, DEFAULT_DST)
    dst_entry.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="w")

    send_button = tk.Button(input_frame, text=_("Senden"), command=send_message)
    send_button.grid(row=0, column=4, rowspan=2, padx=5, pady=5, sticky="ns")

    tk.Label(input_frame, text=_("Letzte Uhrzeit vom Netz (UTC):")).grid(row=0, column=5, padx=5, pady=5, sticky="w")
    net_time = tk.Entry(input_frame, width=25)
    net_time.grid(row=1, column=5, padx=5, pady=5, sticky="w")
    net_time.config(state="disabled")

    # Fülle die Listbox mit den Rufzeichen
    rufzeichen_liste = load_rufzeichen()

    # Erstelle Combobox
    selected_rufzeichen = tk.StringVar()
    combobox = ttk.Combobox(input_frame, textvariable=selected_rufzeichen, values=rufzeichen_liste, state="readonly")
    combobox.grid(row=2, column=5, padx=5, pady=5, sticky="w")

    def on_open_chat():
        selected_value = selected_rufzeichen.get()
        if selected_value:
            create_tab(selected_value)
        else:
            messagebox.showwarning(_("Hinweis"), _("Bitte ein Rufzeichen auswählen!"))


    # Button zum Öffnen des Chats
    open_button = tk.Button(input_frame, text=_("bisherigen Chat öffnen"), command=on_open_chat).grid(row=2, column=6, padx=5, pady=5, sticky="w")
        
        

    tab_control.pack(expand=1, fill="both", padx=10, pady=10)

    threading.Thread(target=receive_messages, daemon=True).start()
    
    reopen_tabs()

    root.mainloop()


if __name__ == "__main__":
    main()
