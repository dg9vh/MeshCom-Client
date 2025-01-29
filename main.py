#!/usr/bin/python3
import os
import configparser
from datetime import datetime
import socket
import json
import threading
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import simpleaudio as sa
import wave
import numpy as np
import collections

# Wir speichern die letzten 20 IDs in einer deque
received_ids = collections.deque(maxlen=5)  # maxlen sorgt dafür, dass nur die letzten 5 IDs gespeichert werden

# Server-Konfiguration
UDP_IP_ADDRESS = "0.0.0.0"
UDP_PORT_NO = 1799

DEFAULT_DST = "*"  # Standardziel für Nachrichten (Broadcast)
DESTINATION_PORT = 1799  # Ziel-Port anpassen
MAX_MESSAGE_LENGTH = 150  # Maximale Länge der Nachricht

# Einstellungen
CONFIG_FILE = "settings.ini"
config = configparser.ConfigParser()

# Dictionary zur Verwaltung der Tabs
tab_frames = {}
tab_highlighted = set()  # Set für Tabs, die hervorgehoben werden sollen
volume = 0.5  # Standardlautstärke (50%)

# Ziel-IP aus Einstellungen laden oder Standardwert setzen
DESTINATION_IP = "192.168.178.28"

# Eigenes Rufzeichen aus Einstellungen laden oder Standardwert setzen
MYCALL = "DG9VH-99"


class SettingsDialog(tk.Toplevel):
    def __init__(self, master, initial_volume, save_callback):
        super().__init__(master)
        self.title("Einstellungen")
        self.geometry("300x200")
        self.resizable(False, False)

        self.save_callback = save_callback

        # Lautstärke-Label
        tk.Label(self, text="Lautstärke (0.0 bis 1.0):").pack(pady=10)

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
        ttk.Button(self, text="Speichern", command=self.save_settings).pack(pady=10)

    def save_settings(self):
        # Lautstärke speichern und zurückgeben
        volume = self.volume_slider.get()
        self.save_callback(volume)
        self.destroy()


def load_settings():
    """Lädt Einstellungen aus der INI-Datei."""
    global DESTINATION_IP, MYCALL, volume
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        DESTINATION_IP = config.get("Settings", "DestinationIP", fallback=DESTINATION_IP)
        MYCALL = config.get("Settings", "MyCall", fallback=MYCALL)
        volume = config.getfloat("Settings", "Volume", fallback=0.5)


def save_settings():
    """Speichert Einstellungen in die INI-Datei."""
    config["Settings"] = {
        "DestinationIP": DESTINATION_IP,
        "MYCALL": MYCALL,
        "Volume": volume,
    }
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)


def open_settings_dialog():
    def save_volume(new_volume):
        global volume
        volume = new_volume
        save_settings()
        print(f"Lautstärke gespeichert: {volume}")

    SettingsDialog(root, volume, save_volume)
    

def play_sound_with_volume(file_path, volume=1.0):
    """
    Spielt eine Sounddatei mit einstellbarer Lautstärke ab.
    :param file_path: Pfad zur WAV-Datei.
    :param volume: Lautstärke (zwischen 0.0 und 1.0).
    """
    try:
        # Öffne die WAV-Datei
        with wave.open(file_path, "rb") as wav_file:
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
        print(f"Fehler beim Abspielen der Sounddatei: {e}")
        

def receive_messages():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((UDP_IP_ADDRESS, UDP_PORT_NO))
    print(f"Server started, listening on {UDP_IP_ADDRESS}:{UDP_PORT_NO}")

    while True:
        try:
            data, addr = server_sock.recvfrom(1024)
            decoded_data = data.decode('utf-8')
            print(f"Received data from {addr}: {decoded_data}")
            json_data = json.loads(decoded_data)
            display_message(json_data)
        except Exception as e:
            print(f"An error occurred: {e}")


def display_message(message):
    src_call = message.get('src', 'Unknown')
    dst_call = message.get('dst', 'Unknown')
    if dst_call == MYCALL:
        dst_call = src_call
    
    if dst_call.find(',') > 0:
        dst_call = dst_call[:dst_call.find(',')]
        
    msg_text = message.get('msg', '')
    message_id = message.get("msg_id", '')
    
    if message_id == '':
        return
    
    if message_id in received_ids:
        print(f"Nachricht mit ID {message_id} bereits empfangen und verarbeitet.")
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
    tab_frames[dst_call].config(state=tk.NORMAL)
    tab_frames[dst_call].insert(tk.END, display_text)
    tab_frames[dst_call].config(state=tk.DISABLED)
    tab_frames[dst_call].yview(tk.END)
    if src_call != "You":
        play_sound_with_volume("klingel.wav", volume)

    # Tab hervorheben
    highlight_tab(dst_call)
    # Nach der Verarbeitung die ID zur deque hinzufügen
    received_ids.append(message_id)


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
        print(f"Error sending message: {e}")
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

    title_label = tk.Label(tab_header, text=f"Ziel: {dst_call}", anchor="w")
    title_label.pack(side=tk.LEFT, padx=5)

    close_button = tk.Button(tab_header, text="X", command=lambda: close_tab(dst_call, tab_frame), width=2)
    close_button.pack(side=tk.RIGHT, padx=5)

    # Textfeld
    text_area = tk.Text(tab_frame, wrap=tk.WORD, state=tk.DISABLED, height=20, width=60)
    text_area.pack(side=tk.LEFT, expand=1, fill="both", padx=10, pady=10)

    scrollbar = tk.Scrollbar(tab_frame, orient=tk.VERTICAL, command=text_area.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text_area.config(yscrollcommand=scrollbar.set)

    tab_frames[dst_call] = text_area


def close_tab(dst_call, tab_frame):
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
    new_ip = simpledialog.askstring("Ziel-IP konfigurieren", "Geben Sie die neue Ziel-IP-Adresse ein:", initialvalue=DESTINATION_IP)
    if new_ip:
        DESTINATION_IP = new_ip
        save_settings()
        messagebox.showinfo("Einstellung gespeichert", f"Neue Ziel-IP: {DESTINATION_IP}")


def configure_mycall():
    """Dialog zur Konfiguration des eigenen Rufzeichens."""
    global MYCALL
    new_mycall = simpledialog.askstring("Eigenes Rufzeichen konfigurieren", "Geben Sie das eigene Rufzeichen mit SSID ein:", initialvalue=MYCALL)
    if new_mycall:
        MYCALL = new_mycall
        save_settings()
        messagebox.showinfo("Einstellung gespeichert", f"Neues Rufzeichen: {MYCALL}")


def show_help():
    """Hilfe anzeigen."""
    messagebox.showinfo("Hilfe", "Dieses Programm ermöglicht den Empfang und das Senden von Nachrichten über das Meshcom-Netzwerk, indem via UDP eine Verbindung zum Node hergestellt wird. Zur Nutzung mit dem Node ist hier vorher auf dem Node mit --extudpip <ip-adresse des Rechners> sowie --extudp on die Datenübertragung zu aktivieren und über die Einstellungen hier die IP-Adresse des Nodes anzugeben.")


def show_about():
    """Über-Dialog anzeigen."""
    messagebox.showinfo("Über", "MeshCom Client\nVersion 1.0\nEntwickelt von DG9VH")


# GUI-Setup
root = tk.Tk()
root.title("MeshCom Client by DG9VH")
root.geometry("800x400")  # Fenstergröße auf 800x400 setzen

load_settings()

# Menüleiste
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

file_menu = tk.Menu(menu_bar, tearoff=0)
file_menu.add_command(label="Beenden", command=root.quit)
menu_bar.add_cascade(label="Datei", menu=file_menu)

settings_menu = tk.Menu(menu_bar, tearoff=0)
settings_menu.add_command(label="Ziel-IP konfigurieren", command=configure_destination_ip)
settings_menu.add_command(label="Eigenes Rufzeichen", command=configure_mycall)
settings_menu.add_command(label="Lautstärke konfigurieren", command=open_settings_dialog)
menu_bar.add_cascade(label="Einstellungen", menu=settings_menu)

help_menu = tk.Menu(menu_bar, tearoff=0)
help_menu.add_command(label="Hilfe", command=show_help)
help_menu.add_command(label="Über", command=show_about)
menu_bar.add_cascade(label="Hilfe", menu=help_menu)

tab_control = ttk.Notebook(root)
tab_control.bind("<<NotebookTabChanged>>", reset_tab_highlight)

input_frame = tk.Frame(root)
input_frame.pack(fill="x", padx=10, pady=5)

tk.Label(input_frame, text="Nachricht:").grid(row=0, column=0, padx=5, pady=5, sticky="e")

vcmd = root.register(validate_length)  # Validation-Command registrieren
message_entry = tk.Entry(input_frame, width=40, validate="key", validatecommand=(vcmd, "%P"))
message_entry.grid(row=0, column=1, padx=5, pady=5)
message_entry.bind("<Return>", send_message) 

tk.Label(input_frame, text="Ziel:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
dst_entry = tk.Entry(input_frame, width=20)
dst_entry.insert(0, DEFAULT_DST)
dst_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

send_button = tk.Button(input_frame, text="Senden", command=send_message)
send_button.grid(row=0, column=2, rowspan=2, padx=5, pady=5, sticky="ns")

tk.Label(input_frame, text="Letzter Uhrzeit vom Netz:").grid(row=0, column=3, padx=5, pady=5, sticky="w")
net_time = tk.Entry(input_frame, width=25)
net_time.grid(row=1, column=3, padx=5, pady=5)
net_time.config(state="disabled")

tab_control.pack(expand=1, fill="both", padx=10, pady=10)

threading.Thread(target=receive_messages, daemon=True).start()

root.mainloop()
