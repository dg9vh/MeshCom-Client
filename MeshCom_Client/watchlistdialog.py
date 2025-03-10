#!/usr/bin/python3
""" Erzeugt den Watchlist-Dialog """
import tkinter as tk
from tkinter import messagebox

class WatchlistDialog(tk.Toplevel):
    """ Öffnet einen Dialog zur Konfiguration der Watchlist """
    def __init__(self, master, save_callback, wl):
        self.watchlist = wl
        super().__init__(master)
        self.title(_("Einstellungen"))
        self.geometry("600x400")
        self.resizable(False, False)

        self.save_callback = save_callback

        tk.Label(self, text=_("Rufzeichen hinzufügen (ohne -SSID):")) \
            .grid(row=0, column=0, sticky="w")

        self.entry_callsign = tk.Entry(self)
        self.entry_callsign.grid(row=0, column=1, padx=5)

        self.btn_add = tk.Button(self, text=_("Hinzufügen"), command=self.add_callsign)
        self.btn_add.grid(row=0, column=2, padx=5)

        self.listbox = tk.Listbox(self, height=10, width=30)
        self.listbox.grid(row=1, column=0, columnspan=2, pady=5)

        self.btn_remove = tk.Button(self, text=_("Löschen"), command=self.remove_callsign)
        self.btn_remove.grid(row=1, column=2, padx=5)

        # Watchlist laden
        for call in self.watchlist:
            self.listbox.insert(tk.END, call)


    def save_watchlist(self):
        """Speichert die aktuelle Watchlist in die Settings"""
        self.save_settings()


    def add_callsign(self):
        """Fügt ein neues Rufzeichen zur Watchlist hinzu."""
        callsign = self.entry_callsign.get().strip().upper()
        if callsign and callsign not in self.watchlist:
            self.watchlist.add(callsign)
            self.listbox.insert(tk.END, callsign)
            self.entry_callsign.delete(0, tk.END)
            self.save_watchlist()
        elif callsign in self.watchlist:
            messagebox.showwarning(_("Warnung"), \
                _("{callsign} ist bereits in der Watchlist.").format(callsign=callsign))


    def remove_callsign(self):
        """Löscht das ausgewählte Rufzeichen aus der Watchlist."""
        selected = self.listbox.curselection()
        if selected:
            callsign = self.listbox.get(selected[0])
            self.watchlist.remove(callsign)
            self.listbox.delete(selected[0])
            self.save_watchlist()


    def save_settings(self):
        """Speichert die Watchlist."""
        # Watchlist speichern und zurückgeben
        self.save_callback(self.watchlist)
        #self.destroy()
