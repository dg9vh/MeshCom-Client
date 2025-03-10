#!/usr/bin/python3
""" Erzeugt den Settings-Dialog """
import tkinter as tk
from tkinter import ttk, filedialog

class SettingsDialog(tk.Toplevel):
    """Öffnet einen Einstellungs-Dialog und setzt die Lautstärke."""
    def __init__(self, \
        master, \
            initial_volume, \
                initial_new_message, \
                    initial_callsign_alert, \
                        initial_owncall_alert, \
                            save_callback):
        self.new_message = initial_new_message
        self.callsign_alert = initial_callsign_alert
        self.own_callsign = initial_owncall_alert
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

        self.new_message_label = \
            tk.Label(self, text = _("Neue Nachricht:") + " " + initial_new_message, width=200)
        self.new_message_label.pack(pady=10)
        ttk.Button(self, text=_("Datei wählen"), \
            command = self.choose_new_message_file).pack(pady=10)

        self.callsign_alert_label = tk.Label(self, \
            text = _("Watchlist-Hinweis:") + " " + initial_callsign_alert, width=200)
        self.callsign_alert_label.pack(pady=10)
        ttk.Button(self, text=_("Datei wählen"), \
            command = self.choose_callsign_alert_file).pack(pady=10)

        self.owncall_alert_label = tk.Label(self, \
            text = _("Eigenes Rufzeichen-Hinweis:") + " " + initial_owncall_alert, width=200)
        self.owncall_alert_label.pack(pady=10)
        ttk.Button(self, text=_("Datei wählen"), \
            command = self.choose_owncall_alert_file).pack(pady=10)

        # Speichern-Button
        ttk.Button(self, text=_("Speichern"), command = self.save_settings).pack(pady=10)


    def choose_new_message_file(self):
        """Öffnet einen Datei-Dialog und setzt die Variable auf den ausgewählten Dateinamen."""
        #global NEW_MESSAGE
        self.new_message = filedialog.askopenfilename(filetypes=[("WAV-Dateien", "*.wav")])
        self.new_message_label.config(text = _("Neue Nachricht:") + " " + self.new_message)


    def choose_callsign_alert_file(self):
        """Öffnet einen Datei-Dialog und setzt die Variable auf den ausgewählten Dateinamen."""
        #global CALLSIGN_ALERT
        self.callsign_alert = filedialog.askopenfilename(filetypes=[("WAV-Dateien", "*.wav")])
        self.callsign_alert_label.config(text = _("Watchlist-Hinweis:") + " " + self.callsign_alert)


    def choose_owncall_alert_file(self):
        """Öffnet einen Datei-Dialog und setzt die Variable auf den ausgewählten Dateinamen."""
        #global OWN_CALLSIGN
        self.own_callsign = filedialog.askopenfilename(filetypes=[("WAV-Dateien", "*.wav")])
        self.owncall_alert_label.config(text = \
            _("Eigenes Rufzeichen-Hinweis:") + " " + self.own_callsign)


    def save_settings(self):
        """ Lautstärke speichern und zurückgeben """
        newvolume = self.volume_slider.get()
        self.save_callback(newvolume, self.new_message, self.callsign_alert, self.own_callsign)
        self.destroy()
