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
import simpleaudio as sa
import wave
import numpy as np
import collections
import gettext


# Versionsnummer
VERSION="1.0.2"

# Wir speichern die letzten 20 IDs in einer deque
received_ids = collections.deque(maxlen=5)  # maxlen sorgt dafür, dass nur die letzten 5 IDs gespeichert werden

# Server-Konfiguration
UDP_IP_ADDRESS = "0.0.0.0"
UDP_PORT_NO = 1799

DEFAULT_DST = "*"  # Standardziel für Nachrichten (Broadcast)
DESTINATION_PORT = 1799  # Ziel-Port anpassen
MAX_MESSAGE_LENGTH = 140  # Maximale Länge der Nachricht

# Einstellungen
current_dir = os.getcwd()
CONFIG_FILE = Path(__file__).parent / 'settings.ini'
config = configparser.ConfigParser()

# Chatlog
CHATLOG_FILE = Path(__file__).parent / 'chatlog.json'


# Dictionary zur Verwaltung der Tabs
tab_frames = {}
tab_highlighted = set()  # Set für Tabs, die hervorgehoben werden sollen

#Set für Watchlist
watchlist = set()

language = "de" # Standardsprache

volume = 0.5  # Standardlautstärke (50%)

# Ziel-IP aus Einstellungen laden oder Standardwert setzen
DESTINATION_IP = "192.168.178.28"

# Eigenes Rufzeichen aus Einstellungen laden oder Standardwert setzen
MYCALL = "DG9VH-99"


class SettingsDialog(tk.Toplevel):
    def __init__(self, master, initial_volume, save_callback):
        super().__init__(master)
        self.title(_("Einstellungen"))
        self.geometry("300x200")
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

        # Speichern-Button
        ttk.Button(self, text=_("Speichern"), command=self.save_settings).pack(pady=10)


    def save_settings(self):
        # Lautstärke speichern und zurückgeben
        volume = self.volume_slider.get()
        self.save_callback(volume)
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
    global DESTINATION_IP, MYCALL, volume, language, watchlist
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        DESTINATION_IP = config.get("Settings", "DestinationIP", fallback=DESTINATION_IP)
        MYCALL = config.get("Settings", "MyCall", fallback=MYCALL)
        volume = config.getfloat("Settings", "Volume", fallback=0.5)
        language = config.get("GUI", "Language", fallback="de")
        watchlist = set(config.get("watchlist", "callsigns", fallback="").split(","))


def save_settings():
    """Speichert Einstellungen in die INI-Datei."""
    config["GUI"] = {
        "language": language,
    }
    config["Settings"] = {
        "DestinationIP": DESTINATION_IP,
        "MYCALL": MYCALL,
        "Volume": volume,
    }
    config["watchlist"] = {"callsigns": ",".join(watchlist)}
    
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)


def open_settings_dialog():
    def save_volume(new_volume):
        global volume
        volume = new_volume
        save_settings()
        print(_("Lautstärke gespeichert: {volume}").format(volume=volume))

    SettingsDialog(root, volume, save_volume)


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
        # Pfad zur Datei in einen String umwandeln
        file_path_str = str(Path(__file__).parent / "sounds" / file_path)
        
        # Öffne die WAV-Datei
        with wave.open(file_path_str, "rb") as wav_file:
            # Lese die WAV-Datei
            frames = wav_file.readframes(wav_file.getnframes())
            sample_width = wav_file.getsampwidth()
            num_channels = wav_file.getnchannels()
            frame_rate = wav_file.getframerate()

        # Konvertiere Frames in ein numpy-Array
        audio_data = np.frombuffer(frames, dtype=np.int16)

        # Passe die Lautstärke an
        audio_data = (audio_data * volume).astype(np.int16)

        # Erstelle eine neue WaveObject-Instanz
        wave_obj = sa.WaveObject(audio_data.tobytes(), num_channels, sample_width, frame_rate)
        play_obj = wave_obj.play()
        play_obj.wait_done()  # Warten, bis der Ton fertig abgespielt ist
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
    
    if dst_call == MYCALL:
        dst_call = src_call
        if  msg_text[-4] == "{":
            msg_tag = msg_text[-3:]
            msg_text = msg_text[:-4]
        
        if msg_text.find("ack") > 0:
                msg_text = msg_text[msg_text.find("ack"):]
                if msg_text[0:3] == "ack" and len(msg_text) == 6:
                    msg_tag = msg_text [-3:]
                    if dst_call.find(',') > 0:
                        dst_call = dst_call[:dst_call.find(',')]
                    tab_frames[dst_call].tag_config(msg_tag, foreground="green")  # Ändere die Farbe
                    #tab_frames[dst_call].insert(msg_tag + " wordend", " ✓")  # Häkchen anfügen
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
    
    add_message(dst_call, display_text)
    
    callsign = extract_callsign(src_call)
    if callsign in watchlist:
        print(_("ALERT: {callsign} erkannt!").format(callsign=callsign))
        play_sound_with_volume('alert.wav', volume)
    elif src_call != "You":
        play_sound_with_volume('klingel.wav', volume)

    # Tab hervorheben
    highlight_tab(dst_call)
    # Nach der Verarbeitung die ID zur deque hinzufügen
    received_ids.append(message_id)


def add_message(call, message):
    if call not in chat_storage:
        chat_storage[call] = []
    chat_storage[call].append(message)
    save_chatlog(chat_storage)  # Speichert die Chats direkt


def send_message(event=None):
    msg_text = message_entry.get()
    msg_text = msg_text.replace('"',"'")
    
    dst_call = dst_entry.get() or DEFAULT_DST

    if not msg_text.strip():
        return

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
    return len(new_text) <= MAX_MESSAGE_LENGTH


def create_tab(dst_call):
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
    text_area.pack(side=tk.LEFT, expand=1, fill="both", padx=10, pady=10)

    scrollbar = tk.Scrollbar(tab_frame, orient=tk.VERTICAL, command=text_area.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text_area.config(yscrollcommand=scrollbar.set)
    
    tab_frames[dst_call] = text_area
    if dst_call in chat_storage:
        print(_("Chat-Historie wiederherstellen"))
        for msg in chat_storage[dst_call]:
            tab_frames[dst_call].config(state=tk.NORMAL)
            tab_frames[dst_call].insert(tk.END, msg) # Chatverlauf in das Text-Widget einfügen
            tab_frames[dst_call].config(state=tk.DISABLED)
            tab_frames[dst_call].yview(tk.END)


def close_tab(dst_call, tab_frame):
    global chat_storage
    save_chatlog(chat_storage) 
    if dst_call in tab_frames:
        del tab_frames[dst_call]
    tab_control.forget(tab_frame)


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


def set_language(lang):
    """Setzt die Sprache in der Config-Datei und gibt eine Meldung aus."""
    global language
    language = lang
    save_settings()
    print (language)
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
    
    
def show_help():
    """Hilfe anzeigen."""
    messagebox.showinfo(_("Hilfe"), _("Dieses Programm ermöglicht den Empfang und das Senden von Nachrichten über das Meshcom-Netzwerk, indem via UDP eine Verbindung zum Node hergestellt wird. Zur Nutzung mit dem Node ist hier vorher auf dem Node mit --extudpip <ip-adresse des Rechners> sowie --extudp on die Datenübertragung zu aktivieren und über die Einstellungen hier die IP-Adresse des Nodes anzugeben."))


def show_about():
    global VERSION
    """Über-Dialog anzeigen."""
    messagebox.showinfo(_("Über"), _("MeshCom Client\nVersion {VERSION}\nEntwickelt von DG9VH").format(VERSION=VERSION))


def on_closing():
    save_chatlog(chat_storage)  # Speichert alle offenen Chats
    root.destroy()  # Schließt das Tkinter-Fenster

def main():
    global root, tab_control, chat_storage, dst_entry, message_entry, net_time
    # GUI-Setup
    root = tk.Tk()
    root.title(f"MeshCom Client {VERSION} by DG9VH")
    root.geometry("920x400")  # Fenstergröße auf 800x400 setzen
    root.protocol("WM_DELETE_WINDOW", on_closing)  # Fängt das Schließen ab

    load_settings()

    appname = 'MeshCom-Client'
    localedir = current_dir + "/locales"

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
    settings_menu.add_command(label=_("Watchlist"), command=open_watchlist_dialog)
    settings_menu.add_command(label=_("Lautstärke konfigurieren"), command=open_settings_dialog)
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
    message_entry.grid(row=0, column=1, padx=5, pady=5)
    message_entry.bind("<Return>", send_message) 

    tk.Label(input_frame, text=_("Ziel:")).grid(row=1, column=0, padx=5, pady=5, sticky="e")
    dst_entry = tk.Entry(input_frame, width=20)
    dst_entry.insert(0, DEFAULT_DST)
    dst_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

    send_button = tk.Button(input_frame, text=_("Senden"), command=send_message)
    send_button.grid(row=0, column=2, rowspan=2, padx=5, pady=5, sticky="ns")

    tk.Label(input_frame, text=_("Letzte Uhrzeit vom Netz (UTC):")).grid(row=0, column=3, padx=5, pady=5, sticky="w")
    net_time = tk.Entry(input_frame, width=25)
    net_time.grid(row=1, column=3, padx=5, pady=5, sticky="w")
    net_time.config(state="disabled")

    # Fülle die Listbox mit den Rufzeichen
    rufzeichen_liste = load_rufzeichen()

    # Erstelle Combobox
    selected_rufzeichen = tk.StringVar()
    combobox = ttk.Combobox(input_frame, textvariable=selected_rufzeichen, values=rufzeichen_liste, state="readonly")
    combobox.grid(row=2, column=3, padx=5, pady=5, sticky="w")

    def on_open_chat():
        selected_value = selected_rufzeichen.get()
        if selected_value:
            create_tab(selected_value)
        else:
            messagebox.showwarning(_("Hinweis"), _("Bitte ein Rufzeichen auswählen!"))


    # Button zum Öffnen des Chats
    open_button = tk.Button(input_frame, text=_("bisherigen Chat öffnen"), command=on_open_chat).grid(row=2, column=4, padx=5, pady=5, sticky="w")
        
        

    tab_control.pack(expand=1, fill="both", padx=10, pady=10)

    threading.Thread(target=receive_messages, daemon=True).start()

    root.mainloop()


if __name__ == "__main__":
    main()
