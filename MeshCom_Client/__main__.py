""" MeshCom_Client communicating with MeshCom-Nodes via UDP"""
#!/usr/bin/python3
import os
import configparser
from datetime import datetime
from pathlib import Path
import socket
import json
import threading
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import time
import sys
from importlib.metadata import version, PackageNotFoundError
import collections
import gettext
import tomllib  # Falls Python < 3.11, dann: import toml
import pygame
from MeshCom_Client.settingsdialog import SettingsDialog
from MeshCom_Client.watchlistdialog import WatchlistDialog


def get_version():
    """Liest die Version aus pyproject.toml"""

    # Prüfen, ob Programm gebündelt ist (PyInstaller)
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS) # pylint: disable=protected-access # Temp-Verzeichnis von PyInstaller
    else:
        base_path = Path(__file__).parent.parent  # Standard-Pfad im normalen Python-Lauf

    toml_path = base_path / "pyproject.toml"

    if toml_path.exists():
        with toml_path.open("rb") as f:
            toml_config = tomllib.load(f)
        return toml_config.get("project", {}).get("version", "0.1.0")  # <== Hier geändert!

    return "unknown"  # Standardwert, falls Datei nicht gefunden wird

__version__ = get_version()
print(f"Programmversion: {__version__}")

if __version__ == "unknown":
    try:
        __version__ = version("MeshCom-Client")
    except PackageNotFoundError:
        __version__ = "unknown"

print(f"MeshCom-Client Version: {__version__}")


LAST_SENT_TIME = 0  # Speichert die Zeit der letzten Nachricht
SEND_DELAY = 40  # Wartezeit zum Senden neuer Nachrichten in Sekunden

# Wir speichern die letzten 20 IDs in einer deque
received_ids = collections.deque(maxlen=5)  # maxlen sorgt dafür, dass nur die letzten 5 IDs
                                            # gespeichert werden
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
tab_highlighted = set()  # Set für Tabs, die hervorgehoben werden sollen

# Dictionary zum Speichern der Text-Widgets für verschiedene Rufzeichen-Tabs
text_areas = {}

#globals
NET_TIME = None
SEND_BUTTON = None
TIMER_LABEL = None
CHARACTERS_LEFT = None
MESSAGE_ENTRY = None
TAB_CONTROL = None
CHAT_STORAGE = None
DST_ENTRY = None
ROOT = None
SETTINGS = None


def load_settings():
    """Lädt Einstellungen aus der INI-Datei und gibt sie als Dictionary zurück."""
    settings = {
        "DESTINATION_IP": "192.168.0.2",
        "MYCALL": "XX0XX-1",
        "VOLUME": 0.5,
        "LANGUAGE": "de",
        "WATCHLIST": set(),
        "NEW_MESSAGE": NEW_MESSAGE,
        "CALLSIGN_ALERT": CALLSIGN_ALERT,
        "OWN_CALLSIGN": OWN_CALLSIGN,
        "SEND_DELAY": 40,
        "OPEN_TABS": []
    }

    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        settings["DESTINATION_IP"] = \
            config.get("Settings", "destinationip", fallback=settings["DESTINATION_IP"])
        settings["MYCALL"] = config.get("Settings", "mycall", fallback=settings["MYCALL"])
        settings["VOLUME"] = config.getfloat("Settings", "volume", fallback=0.5)
        settings["SEND_DELAY"] = \
            max(10, min(config.getint("Settings", "senddelay", fallback=40), 40))
        settings["LANGUAGE"] = config.get("GUI", "language", fallback="de")
        settings["WATCHLIST"] = set(config.get("watchlist", "callsigns", fallback="").split(","))
        settings["OPEN_TABS"] = sorted(set(config.get("tablist", "tabs", fallback="").split(",")))

        settings["NEW_MESSAGE"] = \
            config.get("Audio", "new_message", fallback=settings["NEW_MESSAGE"])
        settings["CALLSIGN_ALERT"] = \
            config.get("Audio", "callsign_alert", fallback=settings["CALLSIGN_ALERT"])
        settings["OWN_CALLSIGN"] = \
            config.get("Audio", "own_callsign", fallback=settings["OWN_CALLSIGN"])

    return settings


def reopen_tabs():
    """ Öffnet die Tabs,wie sie beim Programmende vorlagen """
    #global open_tabs
    for tab in SETTINGS["OPEN_TABS"]:
        create_tab(tab)


def save_settings():
    """ Speichert Einstellungen in die INI-Datei."""
    config["GUI"] = {
        "language": SETTINGS["LANGUAGE"],
    }
    config["Settings"] = {
        "destinationip": SETTINGS["DESTINATION_IP"],
        "mycall": SETTINGS["MYCALL"],
        "colume": SETTINGS["VOLUME"],
        "senddelay": SEND_DELAY,
    }
    config["Audio"] = {
        "new_message": SETTINGS["NEW_MESSAGE"],
        "callsign_alert": SETTINGS["CALLSIGN_ALERT"],
        "own_callsign": SETTINGS["OWN_CALLSIGN"],
    }
    config["watchlist"] = {"callsigns": ",".join(SETTINGS["WATCHLIST"])}
    config["tablist"] = {"tabs": ",".join(tab_frames)}

    with open(CONFIG_FILE, "w", encoding = "UTF8") as configfile:
        config.write(configfile)


def open_settings_dialog():
    """ Liest Einstellungen aus der INI-Datei."""
    def save_audio_settings(new_volume, new_newmessage, new_callsign_alert, new_own_callsign):
        SETTINGS["VOLUME"] = new_volume
        SETTINGS["NEW_MESSAGE"] = new_newmessage
        SETTINGS["CALLSIGN_ALERT"] = new_callsign_alert
        SETTINGS["OWN_CALLSIGN"] = new_own_callsign
        save_settings()
        print(_("Lautstärke gespeichert: {VOLUME}") \
            .format(VOLUME=SETTINGS["VOLUME"]))
        print(_("Neue Nachricht-Hinweis: {NEW_MESSAGE}") \
            .format(NEW_MESSAGE=SETTINGS["NEW_MESSAGE"]))
        print(_("Rufzeichen-Hinweis: {CALLSIGN_ALERT}") \
            .format(CALLSIGN_ALERT=SETTINGS["CALLSIGN_ALERT"]))
        print(_("Eigenes-Rufzeichen-Hinweis: {OWN_CALLSIGN}") \
            .format(OWN_CALLSIGN=SETTINGS["OWN_CALLSIGN"]))

    SettingsDialog(ROOT, SETTINGS["VOLUME"], \
        SETTINGS["NEW_MESSAGE"], \
            SETTINGS["CALLSIGN_ALERT"], \
                SETTINGS["OWN_CALLSIGN"], \
                    save_audio_settings)


def open_watchlist_dialog():
    """ Öffnet die Watchlist-Konfiguration """
    def save_watchlist(new_watchlist):
        SETTINGS["WATCHLIST"] = new_watchlist
        save_settings()
        print(_("Watchlist gespeichert"))

    WatchlistDialog(ROOT, save_watchlist, SETTINGS["WATCHLIST"])


def save_chatlog(chat_data):
    """ Speichert den Chat-Verlauf """
    with open(CHATLOG_FILE, "w", encoding = "UTF8") as f:
        print(_("Speichere Chatverlauf"))
        json.dump(chat_data, f, indent=4)
        print(_("Speichern beendet"))


# Funktion zum Löschen des Chatverlaufs
def delete_chat(rufzeichen, text_widget, tab_control, tab):
    """ Löscht Chatverlauf """
    if rufzeichen in CHAT_STORAGE:
        # Bestätigung einholen
        if messagebox.askyesno(_("Chat löschen"), \
            _("Soll der Chatverlauf für {rufzeichen} wirklich gelöscht werden?") \
                .format(rufzeichen=rufzeichen)):
            # Entferne den Chat aus der Datei
            del CHAT_STORAGE[rufzeichen]
            save_chatlog(CHAT_STORAGE)

            # Entferne den Chat aus der GUI (Textfeld leeren)
            text_widget.delete("1.0", tk.END)

            # Optional: Tab schließen
            tab_control.forget(tab)

            messagebox.showinfo(_("Gelöscht"), \
                _("Chatverlauf für {rufzeichen} wurde gelöscht.").format(rufzeichen=rufzeichen))
    else:
        messagebox.showwarning(_("Nicht gefunden"), \
            _("Kein Chatverlauf für {rufzeichen} vorhanden.").format(rufzeichen=rufzeichen))


def load_chatlog():
    """ Lädt den Chatverlauf """
    if os.path.exists(CHATLOG_FILE):
        with open(CHATLOG_FILE, "r", encoding = "UTF8") as f:
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
    """ Empfang der Nachrichten """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((UDP_IP_ADDRESS, UDP_PORT_NO))
    print(_("Server gestarted, hört auf {UDP_IP_ADDRESS}:{UDP_PORT_NO}") \
        .format(UDP_IP_ADDRESS=UDP_IP_ADDRESS, UDP_PORT_NO=UDP_PORT_NO))

    while True:
        try:
            data, addr = server_sock.recvfrom(1024)
            decoded_data = data.decode('utf-8')
            print(_("Daten empfangen von {addr}: {decoded_data}") \
                .format(addr=addr, decoded_data=decoded_data))
            json_data = json.loads(decoded_data)
            display_message(json_data)
        except Exception as e:
            print(_("Es ist ein Fehler aufgetreten (receive_messages): {e}").format(e=e))


def extract_message_data(message):
    """Extrahiert relevante Nachrichtendaten."""
    src_call = message.get('src', 'Unknown')
    dst_call = message.get('dst', 'Unknown')
    msg_text = message.get('msg', '').replace('"', "'")
    message_id = message.get("msg_id", '')
    return src_call, dst_call, msg_text, message_id


def process_ack_message(msg_text, dst_call):
    """Verarbeitet ACK-Nachrichten und ändert ggf. die GUI."""
    if "ack" in msg_text:
        msg_text = msg_text[msg_text.find("ack"):]
        if msg_text[:3] == "ack" and len(msg_text) == 6:
            msg_tag = msg_text[-3:]
            dst_call = dst_call.split(',')[0]  # Entferne ggf. Kommata
            tab_frames[dst_call].tag_config(msg_tag, foreground="green")
            update_message(dst_call, msg_tag)
            return True  # Nachricht verarbeitet
    return False


def update_net_time(msg_text):
    """Aktualisiert die Netzzeit falls ein {CET}-Tag enthalten ist."""
    if "{CET}" in msg_text:
        NET_TIME.config(state="normal")
        NET_TIME.delete(0, tk.END)
        NET_TIME.insert(0, msg_text[5:])
        NET_TIME.config(state="disabled")
        return True  # Nachricht verarbeitet
    return False


def update_display(dst_call, src_call, msg_text, msg_tag):
    """Fügt Nachricht in das GUI-Tab ein."""
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

    add_message(dst_call, display_text, msg_tag, confirmed=False)


def check_alerts(src_call):
    """Überprüft, ob eine Benachrichtigung abgespielt werden soll."""
    callsign = extract_callsign(src_call)
    if callsign in SETTINGS["WATCHLIST"]:
        print(_("ALERT: {callsign} erkannt!").format(callsign=callsign))
        play_sound_with_volume(CALLSIGN_ALERT, SETTINGS["VOLUME"])
    elif src_call == SETTINGS["MYCALL"]:
        print(_("ALERT: Eigenes Rufzeichen").format(callsign=callsign))
        play_sound_with_volume(OWN_CALLSIGN, SETTINGS["VOLUME"])
    elif src_call != "You":
        print(_("ALERT: Normale Nachricht").format(callsign=callsign))
        play_sound_with_volume(NEW_MESSAGE, SETTINGS["VOLUME"])


def display_message(message):
    """Anzeige der Nachrichten"""
    src_call, dst_call, msg_text, message_id = extract_message_data(message)

    msg_tag = ""
    if dst_call == SETTINGS["MYCALL"]:
        dst_call = src_call
        if msg_text[-4] == "{":
            msg_tag = msg_text[-3:]
            msg_text = msg_text[:-4]

        if process_ack_message(msg_text, dst_call):
            return

    if src_call == SETTINGS["MYCALL"] and msg_text[-4] == "{" \
        and not isinstance(dst_call, int) and dst_call != "*":
        msg_tag = msg_text[-3:]
        msg_text = msg_text[:-4]

    dst_call = dst_call.split(',')[0]

    if not message_id or message_id in received_ids or not msg_text:
        return

    if update_net_time(msg_text):
        return

    update_display(dst_call, src_call, msg_text, msg_tag)
    check_alerts(src_call)

    if src_call != SETTINGS["MYCALL"]:
        highlight_tab(dst_call)
    else:
        reset_tab_highlight(None)

    received_ids.append(message_id)


def add_message(call, message, msg_tag, confirmed=False):
    """ Fügt eine Nachricht in die Chat-Historie ein """
    message_data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "message": message.strip(),
        "msg_tag": msg_tag,
        "confirmed": confirmed
    }

    if call not in CHAT_STORAGE:
        CHAT_STORAGE[call] = []
    CHAT_STORAGE[call].append(message_data)
    save_chatlog(CHAT_STORAGE)  # Speichert die Chats direkt


def update_message(call, msg_tag):
    """ Aktualisiert eine Nachricht in der Historie """
    for entry in CHAT_STORAGE[call]:
        if entry.get("msg_tag") == msg_tag:
            entry["confirmed"] = True

    save_chatlog(CHAT_STORAGE)  # Speichert die Chats direkt


def update_timer():
    """ Aktualisiert den Wartetimer """
    remaining_time = max(0, int(SEND_DELAY - (time.time() - LAST_SENT_TIME)))

    if remaining_time > 0:
        TIMER_LABEL.config(text=f"{remaining_time}s")
        ROOT.after(1000, update_timer)  # Aktualisiert jede Sekunde
    else:
        TIMER_LABEL.config(text=_("Bereit zum Senden"))
        SEND_BUTTON.config(state=tk.NORMAL)  # Button wieder aktivieren


def send_message(event=None):
    """ Versendet Nachricht """
    global LAST_SENT_TIME
    msg_text = MESSAGE_ENTRY.get()
    msg_text = msg_text.replace('"',"'")

    dst_call = DST_ENTRY.get() or DEFAULT_DST
    
    if not msg_text.strip():
        return

    current_time = time.time()

    if current_time - LAST_SENT_TIME < SEND_DELAY:
        return

    LAST_SENT_TIME = current_time
    SEND_BUTTON.config(state=tk.DISABLED)  # Button deaktivieren
    update_timer()  # Countdown aktualisieren

    message = {
        "type": "msg",
        "dst": dst_call,
        "msg": msg_text
    }
    try:
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        encoded_message = json.dumps(message, ensure_ascii=False).encode('utf-8')
        client_sock.sendto(encoded_message, (SETTINGS["DESTINATION_IP"], DESTINATION_PORT))
        display_message({"src": "You", "dst": dst_call, "msg": msg_text})
    except Exception as e:
        print(_("Fehler beim Senden: {e}").format(e=e))
    finally:
        client_sock.close()
        MESSAGE_ENTRY.delete(0, tk.END)


def validate_length(new_text):
    """Validiert die Länge der Eingabe."""
    chars_left = MAX_MESSAGE_LENGTH - len(new_text)
    CHARACTERS_LEFT.config(text = str(chars_left))
    return len(new_text) <= MAX_MESSAGE_LENGTH


def create_tab(dst_call):
    """ Erzeugt einen neuen Tab für ein Rufzeichen """
    tab_frame = ttk.Frame(TAB_CONTROL)
    TAB_CONTROL.add(tab_frame, text=dst_call)

    # Titel und Schließen-Button
    tab_header = tk.Frame(tab_frame)
    tab_header.pack(side=tk.TOP, fill="x")

    title_label = tk.Label(tab_header, text=_("Ziel:") + " " + dst_call, anchor="w")
    title_label.bind("<Button-1>", reset_tab_highlight)
    title_label.pack(side=tk.LEFT, padx=5)

    close_button = tk.Button(tab_header, text="X", \
        command=lambda: close_tab(dst_call, tab_frame), width=2)
    close_button.pack(side=tk.RIGHT, padx=5)

    # Button zum Löschen des Chats
    delete_button = tk.Button(tab_header, text=_("Chat löschen"), \
        command=lambda: delete_chat(dst_call, text_area, TAB_CONTROL, tab_frame))
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
    if dst_call in CHAT_STORAGE:
        print(_("Chat-Historie wiederherstellen"))
        for msg in CHAT_STORAGE[dst_call]:
            confirmed = False
            try:
                if msg['confirmed']:
                    confirmed = msg['confirmed']
                msg_text = msg['message']
                msg_tag = msg_text
                start_index = tab_frames[dst_call].index("end-1c linestart")
                tab_frames[dst_call].config(state=tk.NORMAL)
                tab_frames[dst_call].insert(tk.END, msg_text + "\n")
                tab_frames[dst_call].tag_add(msg_tag, start_index, f"{start_index} lineend")

                if confirmed:
                    tab_frames[dst_call].tag_config(msg_tag, foreground="green")  # Ändere die Farbe
                tab_frames[dst_call].config(state=tk.DISABLED)
                tab_frames[dst_call].yview(tk.END)
            except Exception:
                # Altes Chatlog-Format
                tab_frames[dst_call].config(state=tk.NORMAL)
                tab_frames[dst_call].insert(tk.END, msg) # Chatverlauf in das Text-Widget einfügen
                tab_frames[dst_call].config(state=tk.DISABLED)
                tab_frames[dst_call].yview(tk.END)
    save_settings()


def close_tab(dst_call, tab_frame):
    """ Schließt einen ausgewählten Nachrichtentab """
    save_chatlog(CHAT_STORAGE)
    if dst_call in tab_frames:
        del tab_frames[dst_call]
    TAB_CONTROL.forget(tab_frame)
    save_settings()


def highlight_tab(dst_call):
    """Hervorheben des Tabs, wenn eine neue Nachricht eingegangen ist."""
    for i in range(TAB_CONTROL.index("end")):
        if TAB_CONTROL.tab(i, "text").startswith(dst_call):
            TAB_CONTROL.tab(i, text=f"{dst_call} (neu)")
            tab_highlighted.add(dst_call)
            break


def reset_tab_highlight(event):
    """Zurücksetzen der Markierung, wenn der Tab geöffnet wird."""
    current_tab = TAB_CONTROL.index("current")
    dst_call = TAB_CONTROL.tab(current_tab, "text").replace(" (neu)", "")
    if dst_call in tab_highlighted:
        TAB_CONTROL.tab(current_tab, text=dst_call)
        tab_highlighted.remove(dst_call)
    DST_ENTRY.delete(0, tk.END)
    DST_ENTRY.insert(0, dst_call)


def configure_destination_ip():
    """Dialog zur Konfiguration der Ziel-IP-Adresse."""
    new_ip = simpledialog.askstring(_("Node-IP konfigurieren"), \
        _("Geben Sie die neue Node-IP-Adresse ein:"), initialvalue=SETTINGS["DESTINATION_IP"])
    if new_ip:
        SETTINGS["DESTINATION_IP"] = new_ip
        save_settings()
        messagebox.showinfo(_("Einstellung gespeichert"), \
            _("Neue Node-IP: {DESTINATION_IP}").format(DESTINATION_IP=SETTINGS["DESTINATION_IP"]))


def configure_mycall():
    """Dialog zur Konfiguration des eigenen Rufzeichens."""
    new_mycall = simpledialog.askstring(_("Eigenes Rufzeichen konfigurieren"), \
        _("Geben Sie das eigene Rufzeichen mit SSID ein:"), initialvalue=SETTINGS["MYCALL"])
    if new_mycall:
        SETTINGS["MYCALL"] = new_mycall
        save_settings()
        messagebox.showinfo(_("Einstellung gespeichert"), \
            _("Neues Rufzeichen: {MYCALL}").format(MYCALL=SETTINGS["MYCALL"]))


def configure_senddelay():
    """Dialog zur Konfiguration der Wartezeit."""
    new_send_delay = int(simpledialog.askstring(_("Wartezeit konfigurieren"), \
        _("Geben Sie die neue Wartezeit in Sekundn ein (10 ... 40):"), \
            initialvalue=SETTINGS["SEND_DELAY"]))
    if new_send_delay < 10:
        messagebox.showinfo(_("Einstellung korrigieren"), \
            _("Neue Wartezeit: {new_send_delay} ist zu kurz. Bitte mindestens 10 eingeben!") \
                .format(new_send_delay=new_send_delay))
        configure_senddelay()
        return
    if new_send_delay > 40:
        messagebox.showinfo(_("Einstellung korrigieren"), \
            _("Neue Wartezeit: {new_send_delay} ist zu lang. Bitte maximal 40 eingeben!") \
                .format(new_send_delay=new_send_delay))
        configure_senddelay()
        return
    if new_send_delay:
        SETTINGS["SEND_DELAY"] = new_send_delay
        save_settings()
        messagebox.showinfo(_("Einstellung gespeichert"), \
            _("Neue Wartezeit: {SEND_DELAY}").format(SEND_DELAY=SETTINGS["SEND_DELAY"]))


def set_language(lang):
    """Setzt die Sprache in der Config-Datei und gibt eine Meldung aus."""
    SETTINGS["LANGUAGE"] = lang
    save_settings()
    messagebox.showinfo(_("Sprache geändert"), \
        _("Die Sprache wurde geändert.\nBitte starten Sie das Programm neu."))


def extract_callsign(src):
    """Extrahiert das Basisrufzeichen ohne SSID aus dem src-Feld."""
    return src.split("-")[0]  # Trenne bei '-' und nimm den ersten Teil


def load_rufzeichen():
    """ Lade Rufzeichen aus JSON-Datei """
    try:
        with open(CHATLOG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return list(data.keys())  # Holt alle Rufzeichen als Liste
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def on_message_click(event, dst_call):
    """Wird aufgerufen, wenn eine Nachricht in der TextArea angeklickt wird"""
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

            # Aktuellen Inhalt des Eingabefelds holen
            current_text = MESSAGE_ENTRY.get()

            # Prüfen, ob bereits ein Rufzeichen vorhanden ist
            if ":" in current_text:
                # Falls ja, nur das Rufzeichen ersetzen
                current_text = current_text \
                    .split(":", 1)[1].strip()  # Text hinter dem ersten ":" behalten
            else:
                current_text = ""  # Falls kein ":" existiert, neuen Text setzen

            # Neues Rufzeichen mit dem aktuellen Text setzen
            MESSAGE_ENTRY.delete(0, tk.END)
            MESSAGE_ENTRY.insert(0, f"{sender_callsign}: {current_text}")
            MESSAGE_ENTRY.focus_set()
    except Exception as e:
        print(f"Fehler beim Parsen der Nachricht: {e}")


def show_help():
    """Hilfe anzeigen."""
    messagebox.showinfo(_("Hilfe"), \
        _("Dieses Programm ermöglicht den Empfang und das Senden von Nachrichten \
            über das Meshcom-Netzwerk, indem via UDP eine Verbindung zum Node hergestellt wird. \
                Zur Nutzung mit dem Node ist hier vorher auf dem Node mit --extudpip <ip-adresse des Rechners> \
                    sowie --extudp on die Datenübertragung zu aktivieren und über die Einstellungen hier \
                        die IP-Adresse des Nodes anzugeben."))


def show_about():
    """Über-Dialog anzeigen."""
    messagebox.showinfo(_("Über"), \
        _("MeshCom Client\nVersion {__version__}\nEntwickelt von DG9VH") \
            .format(__version__=__version__))


def on_closing():
    """ Abschließendes beim Beenden des Programms """
    save_chatlog(CHAT_STORAGE)  # Speichert alle offenen Chats
    ROOT.destroy()  # Schließt das Tkinter-Fenster


def beenden():
    """Beendet das Programm"""
    ROOT.quit()

def main():
    """ Hier das Hauptprogramm """
    global ROOT, \
        TAB_CONTROL, \
            CHAT_STORAGE, \
                DST_ENTRY, \
                    MESSAGE_ENTRY, \
                        NET_TIME, \
                            CHARACTERS_LEFT, \
                                TIMER_LABEL, \
                                    SEND_BUTTON, \
                                        SETTINGS
    # GUI-Setup
    ROOT = tk.Tk()
    ROOT.title(f"MeshCom Client {__version__} by DG9VH")
    ROOT.geometry("950x400")  # Fenstergröße auf 950x400 setzen
    ROOT.protocol("WM_DELETE_WINDOW", on_closing)  # Fängt das Schließen ab

    SETTINGS = load_settings()
    appname = 'MeshCom-Client'
    localedir = current_dir / "locales"
    # initialisiere Gettext
    en_i18n = gettext.translation(appname, localedir, \
        fallback=True, languages=[SETTINGS["LANGUAGE"]])
    en_i18n.install()

    CHAT_STORAGE = load_chatlog()  # Lädt vorhandene Chatlogs beim Programmstart

    # Menüleiste
    menu_bar = tk.Menu(ROOT)
    ROOT.config(menu=menu_bar)

    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label=_("Beenden"), command=beenden, accelerator="Ctrl+Q")
    ROOT.bind_all("<Control-q>", lambda event: beenden())
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

    TAB_CONTROL = ttk.Notebook(ROOT)
    TAB_CONTROL.bind("<<NotebookTabChanged>>", reset_tab_highlight)

    input_frame = tk.Frame(ROOT)
    input_frame.pack(fill="x", padx=10, pady=5)

    tk.Label(input_frame, text=_("Nachricht:")).grid(row=0, column=0, padx=5, pady=5, sticky="e")

    vcmd = ROOT.register(validate_length)  # Validation-Command registrieren
    MESSAGE_ENTRY = tk.Entry(input_frame, width=40, validate="key", validatecommand=(vcmd, "%P"))
    MESSAGE_ENTRY.grid(row=0, column=1, columnspan=3, padx=5, pady=5)
    MESSAGE_ENTRY.bind("<Return>", send_message)

    tk.Label(input_frame, text=_("Wartezeit:")).grid(row=1, column=0, padx=5, pady=5, sticky="e")
    TIMER_LABEL = tk.Label(input_frame, text=_("Bereit zum Senden"))
    TIMER_LABEL.grid(row=1, column=1, padx=5, pady=5, sticky="w")

    tk.Label(input_frame, text=_("Zeichen übrig:")) \
        .grid(row=1, column=2, padx=5, pady=5, sticky="e")
    CHARACTERS_LEFT = tk.Label(input_frame, text="149")
    CHARACTERS_LEFT.grid(row=1, column=3, padx=5, pady=5, sticky="w")

    tk.Label(input_frame, text=_("Ziel:")).grid(row=2, column=0, padx=5, pady=5, sticky="e")
    DST_ENTRY = tk.Entry(input_frame, width=20)
    DST_ENTRY.insert(0, DEFAULT_DST)
    DST_ENTRY.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="w")

    SEND_BUTTON = tk.Button(input_frame, text=_("Senden"), command=send_message)
    SEND_BUTTON.grid(row=0, column=4, rowspan=2, padx=5, pady=5, sticky="ns")

    tk.Label(input_frame, text=_("Letzte Uhrzeit vom Netz (UTC):")) \
        .grid(row=0, column=5, padx=5, pady=5, sticky="w")
    NET_TIME = tk.Entry(input_frame, width=25)
    NET_TIME.grid(row=1, column=5, padx=5, pady=5, sticky="w")
    NET_TIME.config(state="disabled")

    # Fülle die Listbox mit den Rufzeichen
    rufzeichen_liste = load_rufzeichen()

    # Erstelle Combobox
    selected_rufzeichen = tk.StringVar()
    combobox = ttk.Combobox(input_frame, \
        textvariable=selected_rufzeichen, \
            values=rufzeichen_liste, state="readonly")
    combobox.grid(row=2, column=5, padx=5, pady=5, sticky="w")

    def on_open_chat():
        selected_value = selected_rufzeichen.get()
        if selected_value:
            create_tab(selected_value)
        else:
            messagebox.showwarning(_("Hinweis"), _("Bitte ein Rufzeichen auswählen!"))

    # Button zum Öffnen des Chats
    tk.Button(input_frame, text=_("bisherigen Chat öffnen"), \
        command=on_open_chat).grid(row=2, column=6, padx=5, pady=5, sticky="w")

    TAB_CONTROL.pack(expand=1, fill="both", padx=10, pady=10)

    threading.Thread(target=receive_messages, daemon=True).start()

    reopen_tabs()

    ROOT.mainloop()


if __name__ == "__main__":
    main()
