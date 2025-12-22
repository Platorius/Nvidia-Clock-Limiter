import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import psutil
import subprocess
import time
import threading
import json
import os
import sys
import ctypes
import atexit
import winreg 
import re
from collections import deque

import pynvml

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY_LIB = True
except ImportError:
    HAS_TRAY_LIB = False

CONFIG_FILE = "config.json"
APP_NAME = "Nvidia Clock Limiter"
VERSION = "1.3.6" # Bugfix: State Reset on Stop/Start & Code Cleanup

COLOR_INACTIVE = "#007acc"
COLOR_STD      = "#76b900"
COLOR_LIM2     = "#FFC400"
COLOR_LIM3     = "#FF6600"
COLOR_UNLOCK   = "#FF0000"
COLOR_DISABLED = "#555555"
BG_DISABLED    = "#f0f0f0"
BG_NORMAL      = "#ffffff"

class GpuSaverApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1250x950")
        self.root.resizable(False, False)
        
        # CLEANUP: Pfad nur einmal berechnen
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.is_running = False
        self.current_mode_name = "Unknown" 
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self.last_state_change_time = time.time()
        self.last_enforce_time = 0

        # Diagnose
        self.check_oscillation_var = tk.BooleanVar(value=False)
        self.state_change_history = deque(maxlen=9) 
        self.last_warning_time = 0 
        self.warning_popup_open = False

        self.nvml_handle = None
        try:
            pynvml.nvmlInit()
            self.nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except pynvml.NVMLError as e:
            messagebox.showerror("NVML Fehler", f"Kritischer Fehler: NVML nicht geladen.\n{e}")
            sys.exit(1)

        self.gpu_name = self.get_gpu_name() 
        
        # --- VARIABLEN ---
        self.lang_var = tk.StringVar(value="Deutsch")
        
        self.autostart_var = tk.BooleanVar(value=False)
        self.start_min_var = tk.BooleanVar(value=False)
        self.close_to_tray_var = tk.BooleanVar(value=False)
        self.auto_limit_manual_var = tk.BooleanVar(value=False)
        self.auto_limit_auto_var = tk.BooleanVar(value=False)
        self.use_dynamic_load_var = tk.BooleanVar(value=False)

        self.enable_lim2_var = tk.BooleanVar(value=False)
        self.enable_lim3_var = tk.BooleanVar(value=False)
        
        self.saved_std_core = ""; self.saved_std_mem = ""
        self.saved_lim2_core = ""; self.saved_lim2_mem = ""
        self.saved_lim3_core = ""; self.saved_lim3_mem = ""
        
        self.list_unlock = []; self.list_lim2 = []; self.list_lim3 = []
        
        # CACHE
        self.cache_apps_unlock = set()
        self.cache_apps_lim2 = set()
        self.cache_apps_lim3 = set()
        self.cache_enable_lim2 = False
        self.cache_enable_lim3 = False
        self.cache_use_dynamic = False
        self.cache_check_oscillation = False
        self.cache_settings_load = {}
        
        self.cache_rate_general = 500
        self.cache_rate_process = 3000

        self.load_history = deque()
        self.state_tier = 0 

        self.translations = {
            "Deutsch": {
                "title": f"{APP_NAME} v{VERSION} - {self.gpu_name}",
                "behavior": "Verhalten & Start",
                "win_start": "Mit Windows starten",
                "tray_start": "Im Tray starten (bei Autostart)",
                "close_tray": "Beim Schließen (X) in den Tray minimieren",
                "auto_man": "Clock-Limits nach manuellem Start automatisch anwenden",
                "auto_win": "Clock-Limits nach Autostart automatisch anwenden",
                "logic": "Steuerungs-Logik",
                "dynamic": "Anhand GPU- und VID-Auslastung steuern",
                "osc_warn": "Warnung bei Teufelskreislauf (Diagnose)",
                "rate_gen": "Allgemeine Abtastrate (ms):",
                "rate_proc": "Abtastrate Programmlisten (ms):",
                "info_btn": "ℹ Erlaubte Taktraten",
                "std_lim": "1. Standard-Limits (Pflicht)",
                "lim2": "2. Limits (Optional)",
                "lim3": "3. Limits (Optional)",
                "enable_prof": "Profil aktivieren",
                "unlock_list": "Takt-Begrenzung aufheben (Unlock):",
                "lim2_list": "2. Limits aktivieren bei:",
                "lim3_list": "3. Limits aktivieren bei:",
                "load_ctrl": "Steuerung per {type}-Last",
                "act_gt": "Aktivieren > (%):",
                "deact_lt": "Deaktivieren < (%):",
                "time": "Zeit (ms):",
                "btn_browse": "Datei...",
                "btn_proc": "Prozess...",
                "btn_rem": "Entfernen",
                "btn_start": "Takt begrenzen",
                "btn_stop": "Begrenzung aufheben",
                "status_off": "Status: Inaktiv",
                "status_mode": "MODUS:",
                "lang_label": "Sprache / Language:",
                "err_std_empty": "Fehler: Das '1. Standard-Limit' darf nicht leer sein!",
                "err_lim2_empty": "Fehler: '2. Limit' ist aktiviert, aber keine MHz Werte eingetragen!",
                "err_lim3_empty": "Fehler: '3. Limit' ist aktiviert, aber keine MHz Werte eingetragen!",
                "msg_osc_title": "Oszillations-Warnung",
                "msg_osc_text": "Achtung: Es wurde ein ständiger Wechsel zwischen Profilen erkannt!\n\nEmpfehlung:\n1. Erhöhen Sie die 'Zeit (ms)' bei Deaktivieren.\n2. Oder senken Sie die %-Grenze bei Deaktivieren.\n\n(Warnung pausiert für 60s)",
                "err_runtime_change": "Aktion verweigert!\n\nBitte beenden Sie zuerst die Taktbegrenzung ('Begrenzung aufheben'), um Profile zu aktivieren oder zu deaktivieren."
            },
            "English": {
                "title": f"{APP_NAME} v{VERSION} - {self.gpu_name}",
                "behavior": "Behavior & Startup",
                "win_start": "Start with Windows",
                "tray_start": "Start in Tray (on Autostart)",
                "close_tray": "Minimize to Tray on Close (X)",
                "auto_man": "Apply limits automatically after manual start",
                "auto_win": "Apply limits automatically after Autostart",
                "logic": "Control Logic",
                "dynamic": "Control via GPU and VID load",
                "osc_warn": "Warn on rapid cycling (Diagnosis)",
                "rate_gen": "General Sampling Rate (ms):",
                "rate_proc": "App List Sampling Rate (ms):",
                "info_btn": "ℹ Supported Clocks",
                "std_lim": "1. Standard Limits (Mandatory)",
                "lim2": "2. Limits (Optional)",
                "lim3": "3. Limits (Optional)",
                "enable_prof": "Enable Profile",
                "unlock_list": "Remove clock limits (Unlock):",
                "lim2_list": "Enable 2. Limits on:",
                "lim3_list": "Enable 3. Limits on:",
                "load_ctrl": "Control via {type} Load",
                "act_gt": "Activate > (%):",
                "deact_lt": "Deactivate < (%):",
                "time": "Time (ms):",
                "btn_browse": "File...",
                "btn_proc": "Process...",
                "btn_rem": "Remove",
                "btn_start": "Limit Clocks",
                "btn_stop": "Remove Limits",
                "status_off": "Status: Inactive",
                "status_mode": "MODE:",
                "lang_label": "Language / Sprache:",
                "err_std_empty": "Error: '1. Standard Limit' must not be empty!",
                "err_lim2_empty": "Error: '2. Limit' is enabled but MHz values are missing!",
                "err_lim3_empty": "Error: '3. Limit' is enabled but MHz values are missing!",
                "msg_osc_title": "Oscillation Warning",
                "msg_osc_text": "Warning: Rapid cycling between profiles detected!\n\nThe program is switching back and forth very quickly.\n\nRecommendation:\n1. Increase 'Time (ms)' for Deactivation.\n2. Or lower the % threshold for Deactivation.\n\n(Warning paused for 60s)",
                "err_runtime_change": "Action denied!\n\nPlease stop the limiter first ('Remove Limits') to enable or disable profiles."
            }
        }

        self.tray_icon = None
        self.load_config()
        self.update_title()
        self.check_autostart_registry()
        atexit.register(self.cleanup)
        
        try:
            self.root.tk.call('ttk::style', 'configure', 'Green.TLabelframe.Label', '-foreground', COLOR_STD, '-font', ('Segoe UI', 10, 'bold'))
            self.root.tk.call('ttk::style', 'configure', 'Yellow.TLabelframe.Label', '-foreground', COLOR_LIM2, '-font', ('Segoe UI', 10, 'bold'))
            self.root.tk.call('ttk::style', 'configure', 'Orange.TLabelframe.Label', '-foreground', COLOR_LIM3, '-font', ('Segoe UI', 10, 'bold'))
            self.root.tk.call('ttk::style', 'configure', 'Red.TLabelframe.Label', '-foreground', COLOR_UNLOCK, '-font', ('Segoe UI', 10, 'bold'))
            self.root.tk.call('ttk::style', 'configure', 'Bold.TLabelframe.Label', '-font', ('Segoe UI', 10, 'bold'))
            self.root.tk.call('ttk::style', 'configure', 'Gray.TLabelframe.Label', '-foreground', COLOR_DISABLED, '-font', ('Segoe UI', 10, 'bold'))
        except: pass 

        self.setup_gui()
        self.update_ui_states() 

        # CLEANUP: first_load entfernt, Autostart-Logik optimiert
        if "--autostart" in sys.argv:
            if "--minimized" in sys.argv: self.root.after(0, self.minimize_to_tray)
            if self.auto_limit_auto_var.get(): self.root.after(500, self.toggle_monitoring)
        elif self.auto_limit_manual_var.get():
            self.root.after(500, self.toggle_monitoring)

    def update_title(self):
        T = self.translations[self.lang_var.get()]
        self.root.title(T["title"])

    def change_language(self, event=None):
        self.save_config() 
        self.load_config()
        self.update_title()
        self.setup_gui()
        self.update_ui_states() 

    def on_oscillation_toggle(self):
        self.save_config()
        self.last_warning_time = 0
        self.state_change_history.clear()

    # --- UI STATE UPDATE ---
    def update_ui_states(self):
        en2 = self.enable_lim2_var.get()
        if not en2:
            self.enable_lim3_var.set(False) 
        
        en3 = self.enable_lim3_var.get()
        if en3 and not en2:
            self.enable_lim2_var.set(True) 
            en2 = True

        st2 = "normal" if en2 else "disabled"
        bg2 = BG_NORMAL if en2 else BG_DISABLED
        style2 = "Yellow.TLabelframe" if en2 else "Gray.TLabelframe"
        
        self.entry_lim2_core.config(state=st2)
        self.entry_lim2_mem.config(state=st2)
        
        self.frame_lim2.config(style=style2)
        self.frame_list_lim2.config(style=style2) 
        
        self.lbox_lim2.config(bg=bg2)
        self.entry_lim2_act.config(state=st2)
        self.entry_lim2_act_time.config(state=st2)
        self.entry_lim2_deact.config(state=st2)
        self.entry_lim2_deact_time.config(state=st2)
        
        for btn in self.btns_lim2: btn.config(state=st2)
        
        st3 = "normal" if en3 else "disabled"
        bg3 = BG_NORMAL if en3 else BG_DISABLED
        style3 = "Orange.TLabelframe" if en3 else "Gray.TLabelframe"
        
        self.entry_lim3_core.config(state=st3)
        self.entry_lim3_mem.config(state=st3)
        
        self.frame_lim3.config(style=style3)
        self.frame_list_lim3.config(style=style3)
        
        self.lbox_lim3.config(bg=bg3)
        self.entry_lim3_act.config(state=st3)
        self.entry_lim3_act_time.config(state=st3)
        self.entry_lim3_deact.config(state=st3)
        self.entry_lim3_deact_time.config(state=st3)
        
        for btn in self.btns_lim3: btn.config(state=st3)

        self.save_config()

    def on_lim_check_click(self):
        T = self.translations[self.lang_var.get()]
        if self.is_running:
            messagebox.showerror("Error", T["err_runtime_change"])
            self.enable_lim2_var.set(self.cache_enable_lim2)
            self.enable_lim3_var.set(self.cache_enable_lim3)
            return
        self.update_ui_states()

    def validate_and_correct_rates(self, event=None):
        for entry in [self.entry_rate_general, self.entry_rate_process]:
            try:
                if not entry.winfo_exists(): continue 
                
                val = int(entry.get())
                if val < 100:
                    entry.delete(0, tk.END)
                    entry.insert(0, "100")
            except:
                try:
                    entry.delete(0, tk.END)
                    if entry == self.entry_rate_general: entry.insert(0, "500")
                    else: entry.insert(0, "3000")
                except: pass

    def setup_gui(self):
        for widget in self.root.winfo_children(): widget.destroy()
        T = self.translations[self.lang_var.get()]

        header_frame = tk.Frame(self.root, bg="#2d2d2d", height=50)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text=f"{self.gpu_name}".upper(), bg="#2d2d2d", fg=COLOR_STD, font=("Segoe UI", 13, "bold")).pack(pady=12)

        # OBEN
        opts_frame_top = ttk.LabelFrame(self.root, text=T["behavior"], style="Bold.TLabelframe")
        opts_frame_top.pack(padx=10, pady=(0, 10), fill="x")
        r1 = ttk.Frame(opts_frame_top); r1.pack(fill="x", padx=5, pady=2)
        ttk.Checkbutton(r1, text=T["win_start"], variable=self.autostart_var, command=self.update_autostart_registry).pack(side="left", padx=(0,15))
        ttk.Checkbutton(r1, text=T["tray_start"], variable=self.start_min_var, command=self.update_autostart_registry).pack(side="left", padx=(0,15))
        lang_f = ttk.Frame(r1); lang_f.pack(side="right")
        ttk.Label(lang_f, text=T["lang_label"]).pack(side="left", padx=5)
        lang_cb = ttk.Combobox(lang_f, textvariable=self.lang_var, values=["Deutsch", "English"], width=10, state="readonly")
        lang_cb.pack(side="left"); lang_cb.bind("<<ComboboxSelected>>", self.change_language)
        r2 = ttk.Frame(opts_frame_top); r2.pack(fill="x", padx=5, pady=2)
        ttk.Checkbutton(r2, text=T["close_tray"], variable=self.close_to_tray_var, command=self.save_config).pack(side="left", padx=(0,15))
        ttk.Checkbutton(r2, text=T["auto_man"], variable=self.auto_limit_manual_var, command=self.save_config).pack(side="left", padx=(0,15))
        ttk.Checkbutton(r2, text=T["auto_win"], variable=self.auto_limit_auto_var, command=self.save_config).pack(side="left")
        
        # MITTE
        opts_frame_bottom = ttk.LabelFrame(self.root, text=T["logic"], style="Bold.TLabelframe")
        opts_frame_bottom.pack(padx=10, pady=(0, 10), fill="x")
        r3 = ttk.Frame(opts_frame_bottom); r3.pack(fill="x", padx=5, pady=2)
        ttk.Checkbutton(r3, text=T["dynamic"], variable=self.use_dynamic_load_var, command=self.save_config).pack(side="left", padx=(0, 15))
        ttk.Checkbutton(r3, text=T["osc_warn"], variable=self.check_oscillation_var, command=self.on_oscillation_toggle).pack(side="left", padx=(0, 15))
        ttk.Button(opts_frame_bottom, text=T["info_btn"], command=self.show_hardware_info).pack(side="right", padx=5, pady=5)

        r4 = ttk.Frame(opts_frame_bottom); r4.pack(fill="x", padx=5, pady=(5,5))
        
        ttk.Label(r4, text=T["rate_gen"]).pack(side="left", padx=(0, 5))
        self.entry_rate_general = ttk.Entry(r4, width=6)
        self.entry_rate_general.insert(0, self.config_data.get("rate_general", "500"))
        self.entry_rate_general.pack(side="left", padx=(0, 20))
        self.entry_rate_general.bind("<FocusOut>", self.validate_and_correct_rates)
        self.entry_rate_general.bind("<Return>", self.validate_and_correct_rates)

        ttk.Label(r4, text=T["rate_proc"]).pack(side="left", padx=(0, 5))
        self.entry_rate_process = ttk.Entry(r4, width=6)
        self.entry_rate_process.insert(0, self.config_data.get("rate_process", "3000"))
        self.entry_rate_process.pack(side="left")
        self.entry_rate_process.bind("<FocusOut>", self.validate_and_correct_rates)
        self.entry_rate_process.bind("<Return>", self.validate_and_correct_rates)

        # UNTEN
        settings_container = ttk.Frame(self.root)
        settings_container.pack(padx=10, pady=10, fill="x")

        # STANDARD
        frame_std = ttk.LabelFrame(settings_container, text=T["std_lim"], style="Green.TLabelframe")
        frame_std.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.create_entry_pair(frame_std, "std", self.saved_std_core, self.saved_std_mem)

        # LIMIT 2
        self.frame_lim2 = ttk.LabelFrame(settings_container, text=T["lim2"], style="Gray.TLabelframe")
        self.frame_lim2.pack(side="left", fill="both", expand=True, padx=5)
        chk2 = ttk.Checkbutton(self.frame_lim2, text=T["enable_prof"], variable=self.enable_lim2_var, command=self.on_lim_check_click)
        chk2.grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
        self.create_entry_pair(self.frame_lim2, "lim2", self.saved_lim2_core, self.saved_lim2_mem, start_row=1)

        # LIMIT 3
        self.frame_lim3 = ttk.LabelFrame(settings_container, text=T["lim3"], style="Gray.TLabelframe")
        self.frame_lim3.pack(side="left", fill="both", expand=True, padx=(5, 0))
        chk3 = ttk.Checkbutton(self.frame_lim3, text=T["enable_prof"], variable=self.enable_lim3_var, command=self.on_lim_check_click)
        chk3.grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
        self.create_entry_pair(self.frame_lim3, "lim3", self.saved_lim3_core, self.saved_lim3_mem, start_row=1)

        # LISTEN
        lists_container = ttk.Frame(self.root)
        lists_container.pack(padx=10, pady=5, fill="both", expand=True)

        f1 = ttk.Frame(lists_container); f1.pack(side="left", fill="both", expand=True, padx=(0,5))
        self.build_list_ui(f1, T["unlock_list"], self.list_unlock, "unlock")
        self.build_load_ui(f1, "unlock", "GPU")

        f2 = ttk.Frame(lists_container); f2.pack(side="left", fill="both", expand=True, padx=5)
        self.build_list_ui(f2, T["lim2_list"], self.list_lim2, "lim2")
        self.build_load_ui(f2, "lim2", "VID")

        f3 = ttk.Frame(lists_container); f3.pack(side="left", fill="both", expand=True, padx=(5,0))
        self.build_list_ui(f3, T["lim3_list"], self.list_lim3, "lim3")
        self.build_load_ui(f3, "lim3", "VID")

        ctrl_frame = ttk.Frame(self.root)
        ctrl_frame.pack(padx=15, pady=15, fill="x")
        self.status_label = tk.Label(ctrl_frame, text=T["status_off"], fg=COLOR_INACTIVE, font=("Segoe UI", 10, "bold"))
        self.status_label.pack(side="top", pady=(0, 5))
        
        btn_txt = T["btn_stop"] if self.is_running else T["btn_start"]
        self.btn_start = ttk.Button(ctrl_frame, text=btn_txt, command=self.toggle_monitoring)
        self.btn_start.pack(fill="x", ipady=8)

        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close_attempt)

    def create_entry_pair(self, parent, key, def_c, def_m, start_row=0):
        e_c = ttk.Entry(parent, width=8)
        e_c.insert(0, def_c) 
        e_m = ttk.Entry(parent, width=8)
        e_m.insert(0, def_m)
        
        ttk.Label(parent, text="Core:").grid(row=start_row, column=0, padx=5, pady=5)
        e_c.grid(row=start_row, column=1, padx=5, pady=5)
        ttk.Label(parent, text="VRAM:").grid(row=start_row+1, column=0, padx=5, pady=5)
        e_m.grid(row=start_row+1, column=1, padx=5, pady=5)
        setattr(self, f"entry_{key}_core", e_c)
        setattr(self, f"entry_{key}_mem", e_m)

    def build_list_ui(self, parent, title, source, ltype):
        T = self.translations[self.lang_var.get()]
        style_name = "Bold.TLabelframe"
        if ltype == "unlock": style_name = "Red.TLabelframe"

        c = ttk.LabelFrame(parent, text=title, style=style_name)
        c.pack(fill="both", expand=True)
        
        if ltype == "lim2": self.frame_list_lim2 = c
        elif ltype == "lim3": self.frame_list_lim3 = c

        lf = ttk.Frame(c); lf.pack(fill="both", expand=True, padx=5, pady=5)
        sc = ttk.Scrollbar(lf); sc.pack(side="right", fill="y")
        lb = tk.Listbox(lf, height=6, yscrollcommand=sc.set, font=("Consolas", 9))
        lb.pack(side="left", fill="both", expand=True); sc.config(command=lb.yview)
        for x in source: lb.insert(tk.END, x)
        
        if ltype=="unlock": self.lbox_unlock = lb
        elif ltype=="lim2": self.lbox_lim2 = lb
        elif ltype=="lim3": self.lbox_lim3 = lb
        
        tf = ttk.Frame(c); tf.pack(fill="x", padx=5, pady=5)
        b1 = ttk.Button(tf, text=T["btn_browse"], command=lambda: self.browse_file(lb))
        b1.pack(side="left", fill="x", expand=True)
        b2 = ttk.Button(tf, text=T["btn_proc"], command=lambda: self.open_process_picker(lb))
        b2.pack(side="left", fill="x", expand=True)
        b3 = ttk.Button(c, text=T["btn_rem"], command=lambda: self.remove_entry(lb))
        b3.pack(fill="x", padx=5, pady=(0,5))

        if ltype == "lim2": self.btns_lim2 = [b1, b2, b3]
        elif ltype == "lim3": self.btns_lim3 = [b1, b2, b3]

    def build_load_ui(self, parent, key, label_type):
        T = self.translations[self.lang_var.get()]
        f = ttk.LabelFrame(parent, text=T["load_ctrl"].format(type=label_type))
        f.pack(fill="x", pady=(5,0))
        r1 = ttk.Frame(f); r1.pack(fill="x", pady=2)
        ttk.Label(r1, text=T["act_gt"]).pack(side="left")
        e_a = ttk.Entry(r1, width=5); e_a.pack(side="left")
        ttk.Label(r1, text=T["time"]).pack(side="left")
        e_at = ttk.Entry(r1, width=6); e_at.pack(side="left")
        r2 = ttk.Frame(f); r2.pack(fill="x", pady=2)
        ttk.Label(r2, text=T["deact_lt"]).pack(side="left")
        e_d = ttk.Entry(r2, width=5); e_d.pack(side="left")
        ttk.Label(r2, text=T["time"]).pack(side="left")
        e_dt = ttk.Entry(r2, width=6); e_dt.pack(side="left")
        
        setattr(self, f"entry_{key}_act", e_a); setattr(self, f"entry_{key}_act_time", e_at)
        setattr(self, f"entry_{key}_deact", e_d); setattr(self, f"entry_{key}_deact_time", e_dt)
        
        def sv(e, v): 
            e.delete(0, tk.END); e.insert(0, str(v))
        
        sv(e_a, self.config_data.get(f"{key}_act", "90"))
        sv(e_at, self.config_data.get(f"{key}_act_time", "1000"))
        sv(e_d, self.config_data.get(f"{key}_deact", "30"))
        sv(e_dt, self.config_data.get(f"{key}_deact_time", "3000"))

    # --- HELFER FUNKTION ---
    def record_state_change(self, new_tier):
        if self.cache_check_oscillation:
            now_t = time.time()
            self.state_change_history.append((new_tier, now_t))
            self.check_for_oscillation()

    def update_runtime_cache(self):
        self.validate_and_correct_rates()
        try:
            self.cache_apps_unlock = set([x.lower() for x in self.lbox_unlock.get(0, tk.END)])
            self.cache_apps_lim2 = set([x.lower() for x in self.lbox_lim2.get(0, tk.END)])
            self.cache_apps_lim3 = set([x.lower() for x in self.lbox_lim3.get(0, tk.END)])
        except: pass
        
        self.cache_enable_lim2 = self.enable_lim2_var.get()
        self.cache_enable_lim3 = self.enable_lim3_var.get()
        self.cache_use_dynamic = self.use_dynamic_load_var.get()
        self.cache_check_oscillation = self.check_oscillation_var.get()

        def gv(k): return self.get_val(k)
        self.cache_settings_load = {
            "unlock_act": gv("unlock_act"), "unlock_act_time": gv("unlock_act_time"),
            "lim3_act": gv("lim3_act"), "lim3_act_time": gv("lim3_act_time"),
            "lim2_act": gv("lim2_act"), "lim2_act_time": gv("lim2_act_time"),
            "unlock_deact": gv("unlock_deact"), "unlock_deact_time": gv("unlock_deact_time"),
            "lim3_deact": gv("lim3_deact"), "lim3_deact_time": gv("lim3_deact_time"),
            "lim2_deact": gv("lim2_deact"), "lim2_deact_time": gv("lim2_deact_time"),
        }
        
        try: self.cache_rate_general = int(self.entry_rate_general.get())
        except: self.cache_rate_general = 500
        try: self.cache_rate_process = int(self.entry_rate_process.get())
        except: self.cache_rate_process = 3000

    # --- DIAGNOSE FUNKTION ---
    def check_for_oscillation(self):
        if len(self.state_change_history) < 9: return

        history = list(self.state_change_history)
        fast_switches = 0
        s = self.cache_settings_load
        
        for i in range(1, len(history)):
            tier_now, time_now = history[i]
            tier_prev, time_prev = history[i-1]
            time_diff = (time_now - time_prev) * 1000 
            
            limit_ref = 0
            if tier_now < tier_prev:
                if tier_prev == 3: limit_ref = s["unlock_deact_time"]
                elif tier_prev == 2: limit_ref = s["lim3_deact_time"]
                elif tier_prev == 1: limit_ref = s["lim2_deact_time"]
            elif tier_now > tier_prev:
                if tier_now == 3: limit_ref = s["unlock_act_time"]
                elif tier_now == 2: limit_ref = s["lim3_act_time"]
                elif tier_now == 1: limit_ref = s["lim2_act_time"]

            threshold = limit_ref + 3000 
            
            if limit_ref > 0 and time_diff < threshold:
                fast_switches += 1

        if fast_switches >= 8:
            self.trigger_warning()

    def _show_warning_modal(self):
        T = self.translations[self.lang_var.get()]
        messagebox.showwarning(T["msg_osc_title"], T["msg_osc_text"])
        self.warning_popup_open = False 

    def trigger_warning(self):
        if self.warning_popup_open: return
        if time.time() < self.last_warning_time + 60: return

        self.last_warning_time = time.time()
        self.warning_popup_open = True 
        self.state_change_history.clear()
        
        self.root.after(0, self._show_warning_modal)

    # --- CORE LOOP HELPERS ---
    def get_avg_load(self, load_type, ms_duration):
        # NUR DURCHSCHNITT (AVERAGE)
        if not self.load_history: return 0
        now = time.time()
        total = 0; count = 0
        idx = 1 if load_type == 'gpu' else 2
        for entry in reversed(self.load_history):
            t_stamp, l_gpu, l_vid = entry
            if (now - t_stamp) * 1000 > float(ms_duration): break
            total += (l_gpu if idx == 1 else l_vid)
            count += 1
        return (total / count) if count > 0 else 0

    def update_status_text(self, text, color):
        self.status_label.config(text=text, fg=color)

    def loop(self):
        current_list_tier = 0 
        next_process_scan_time = 0
        s = self.cache_settings_load 

        while not self.stop_event.is_set():
            start_t = time.time()
            c, m, p, ug, uv = self.get_gpu_status()
            self.load_history.append((start_t, ug, uv))
            while self.load_history and (start_t - self.load_history[0][0]) > 10: self.load_history.popleft()

            # 1. PROCESS SCANNER (Slow)
            if start_t > next_process_scan_time:
                next_process_scan_time = start_t + (self.cache_rate_process / 1000.0) 
                current_list_tier = 0
                try:
                    for proc in psutil.process_iter(['name']):
                        try:
                            pn = proc.info['name'].lower()
                            if pn in self.cache_apps_unlock: 
                                current_list_tier = 3; break
                            elif self.cache_enable_lim3 and pn in self.cache_apps_lim3: 
                                current_list_tier = max(current_list_tier, 2)
                            elif self.cache_enable_lim2 and pn in self.cache_apps_lim2: 
                                current_list_tier = max(current_list_tier, 1)
                        except: pass
                except: pass

            # 2. STATE MACHINE (FSM Logic)
            target_tier = self.state_tier
            L_Tier = current_list_tier
            use_dyn = self.cache_use_dynamic
            
            # Helper zur Prüfung der "Guard Time" (Wartezeit nach Wechsel)
            time_in_state_ms = (time.time() - self.last_state_change_time) * 1000
            
            # --- SZENARIO A: Wir sind im Standard (0) ---
            if self.state_tier == 0:
                # HOCHSCHALTEN (Jedes Ziel hat eigene Sperrfrist)
                
                # Check Unlock
                if time_in_state_ms > s["unlock_act_time"]:
                    if L_Tier == 3 or (use_dyn and self.get_avg_load("gpu", s["unlock_act_time"]) > s["unlock_act"]):
                        target_tier = 3
                
                # Check Lim 3 (Falls Unlock nicht getriggert)
                if target_tier == 0 and self.cache_enable_lim3 and time_in_state_ms > s["lim3_act_time"]:
                    if L_Tier == 2 or (use_dyn and self.get_avg_load("vid", s["lim3_act_time"]) > s["lim3_act"]):
                        target_tier = 2
                
                # Check Lim 2 (Falls Unlock/Lim3 nicht getriggert)
                if target_tier == 0 and self.cache_enable_lim2 and time_in_state_ms > s["lim2_act_time"]:
                    if L_Tier == 1 or (use_dyn and self.get_avg_load("vid", s["lim2_act_time"]) > s["lim2_act"]):
                        target_tier = 1
            
            # --- SZENARIO B: Wir sind im Unlock (3) ---
            elif self.state_tier == 3:
                # RUNTERSCHALTEN
                stay = False
                
                # ZWINGENDE WARTEZEIT (DEACT GUARD)
                if time_in_state_ms < s["unlock_deact_time"]:
                    stay = True # Sperrfrist läuft -> Bleiben
                else:
                    # Zeit abgelaufen -> Durchschnitt prüfen
                    if L_Tier == 3: stay = True
                    elif use_dyn and self.get_avg_load("gpu", s["unlock_deact_time"]) >= s["unlock_deact"]: stay = True
                
                if not stay: target_tier = 2

            # --- SZENARIO C: Wir sind im 3. Limit (2) ---
            elif self.state_tier == 2:
                # HOCH (zu Unlock)
                if time_in_state_ms > s["unlock_act_time"]:
                    if L_Tier == 3 or (use_dyn and self.get_avg_load("gpu", s["unlock_act_time"]) > s["unlock_act"]):
                        target_tier = 3

                # RUNTER (zu Lim 2) - Nur wenn nicht hochgeschaltet
                if target_tier == 2:
                    stay = False
                    # ZWINGENDE WARTEZEIT (DEACT GUARD)
                    if time_in_state_ms < s["lim3_deact_time"]:
                        stay = True
                    else:
                        if L_Tier == 2: stay = True
                        elif use_dyn:
                            if self.get_avg_load("gpu", s["lim3_deact_time"]) >= s["lim3_deact"]: stay = True
                            elif self.get_avg_load("vid", s["lim3_deact_time"]) >= s["lim3_deact"]: stay = True
                    
                    if not stay or not self.cache_enable_lim3:
                        target_tier = 1
            
            # --- SZENARIO D: Wir sind im 2. Limit (1) ---
            elif self.state_tier == 1:
                # HOCH (zu Unlock)
                if time_in_state_ms > s["unlock_act_time"]:
                    if L_Tier == 3 or (use_dyn and self.get_avg_load("gpu", s["unlock_act_time"]) > s["unlock_act"]):
                        target_tier = 3
                
                # HOCH (zu Lim 3)
                if target_tier == 1 and self.cache_enable_lim3 and time_in_state_ms > s["lim3_act_time"]:
                    if L_Tier == 2 or (use_dyn and self.get_avg_load("vid", s["lim3_act_time"]) > s["lim3_act"]):
                        target_tier = 2

                # RUNTER (zu Standard)
                if target_tier == 1:
                    stay = False
                    # ZWINGENDE WARTEZEIT (DEACT GUARD)
                    if time_in_state_ms < s["lim2_deact_time"]:
                        stay = True
                    else:
                        if L_Tier == 1: stay = True
                        elif use_dyn:
                            if self.get_avg_load("gpu", s["lim2_deact_time"]) >= s["lim2_deact"]: stay = True
                            elif self.get_avg_load("vid", s["lim2_deact_time"]) >= s["lim2_deact"]: stay = True
                    
                    if not stay or not self.cache_enable_lim2:
                        target_tier = 0

            # --- CHANGE EXECUTION ---
            if target_tier != self.state_tier:
                self.state_tier = target_tier
                self.last_state_change_time = time.time()
                self.record_state_change(self.state_tier) 

            # --- APPLY LIMITS ---
            final_tier = self.state_tier
            t_str = "Standard"; t_col = COLOR_STD
            c_req, m_req = self.entry_std_core.get(), self.entry_std_mem.get()
            
            if final_tier == 3: t_str = "Performance"; t_col = COLOR_UNLOCK
            elif final_tier == 2:
                t_str = "3. Limit"; t_col = COLOR_LIM3
                c_req, m_req = self.entry_lim3_core.get(), self.entry_lim3_mem.get()
            elif final_tier == 1:
                t_str = "2. Limit"; t_col = COLOR_LIM2
                c_req, m_req = self.entry_lim2_core.get(), self.entry_lim2_mem.get()

            if t_str != self.current_mode_name:
                self.current_mode_name = t_str
                if final_tier == 3: self.reset_limits()
                else: self.set_limits_force(c_req, m_req)
                self.update_tray_color(t_col)
            elif final_tier != 3: 
                 if (time.time() - self.last_enforce_time) > 5.0:
                     self.enforce_limits_smart(c_req, m_req)
                     self.last_enforce_time = time.time()

            T = self.translations[self.lang_var.get()]
            
            try:
                if self.root.state() == 'normal':
                    final_txt = f"{T['status_mode']} {t_str} [{p}] | {c}/{m} MHz | GPU: {ug}% VID: {uv:.0f}%"
                    self.root.after(0, self.update_status_text, final_txt, t_col)
            except: pass

            try:
                wait_ms = self.cache_rate_general
            except: wait_ms = 500
            time.sleep(wait_ms / 1000.0)

    # --- REST UNVERÄNDERT ---
    def toggle_monitoring(self):
        T = self.translations[self.lang_var.get()]
        if not self.is_running:
            if not self.entry_std_core.get() or not self.entry_std_mem.get():
                messagebox.showerror("Error", T["err_std_empty"])
                return
            if self.enable_lim2_var.get() and (not self.entry_lim2_core.get() or not self.entry_lim2_mem.get()):
                messagebox.showerror("Error", T["err_lim2_empty"])
                return
            if self.enable_lim3_var.get() and (not self.entry_lim3_core.get() or not self.entry_lim3_mem.get()):
                messagebox.showerror("Error", T["err_lim3_empty"])
                return

            self.update_runtime_cache() 
            self.is_running = True; self.stop_event.clear(); self.btn_start.config(text=T["btn_stop"])
            
            # BUGFIX: Status und Zeitstempel beim Start zurücksetzen!
            self.state_tier = 0
            self.last_state_change_time = time.time()
            
            self.monitor_thread = threading.Thread(target=self.loop, daemon=True); self.monitor_thread.start()
        else:
            self.is_running = False; self.stop_event.set(); self.btn_start.config(text=T["btn_start"])
            
            # BUGFIX: Status beim Stoppen auch sauber zurücksetzen
            self.state_tier = 0
            self.last_state_change_time = time.time()
            
            self.status_label.config(text=T["status_off"], fg=COLOR_INACTIVE); self.reset_limits(); self.current_mode_name = "Unknown"; self.update_tray_color(COLOR_INACTIVE); self.load_history.clear()
            self.state_change_history.clear() 

    def run_smi(self, args):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(["nvidia-smi"] + args, startupinfo=startupinfo, creationflags=0x08000000, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass
    def get_gpu_status(self):
        try:
            c = pynvml.nvmlDeviceGetClockInfo(self.nvml_handle, pynvml.NVML_CLOCK_GRAPHICS)
            m = pynvml.nvmlDeviceGetClockInfo(self.nvml_handle, pynvml.NVML_CLOCK_MEM)
            rates = pynvml.nvmlDeviceGetUtilizationRates(self.nvml_handle)
            ug = rates.gpu
            try:
                ue = pynvml.nvmlDeviceGetEncoderUtilization(self.nvml_handle)[0]
                ud = pynvml.nvmlDeviceGetDecoderUtilization(self.nvml_handle)[0]
            except: ue = 0; ud = 0
            uv = max(ue, ud) * 2
            try:
                p_state = pynvml.nvmlDeviceGetPowerState(self.nvml_handle)
                p = f"P{p_state}"
            except: p = "P?"
            return c, m, p, ug, uv
        except: return 0, 0, "Err", 0, 0
    def enforce_limits_smart(self, core, mem):
        if not core or not mem: return
        try:
            tc, tm = int(core), int(mem)
            cc, cm, _, _, _ = self.get_gpu_status()
            if cc > (tc + 50): self.run_smi(["-lgc", str(tc)]); time.sleep(0.05)
            if cm > (tm + 50): self.run_smi(["-lmc", str(tm)])
        except: pass
    def set_limits_force(self, core, mem):
        if core: self.run_smi(["-lgc", core]); time.sleep(0.05)
        if mem: self.run_smi(["-lmc", mem])
    def reset_limits(self):
        self.run_smi(["-rgc"]); time.sleep(0.05); self.run_smi(["-rmc"])
    def cleanup(self):
        self.reset_limits()
        try: pynvml.nvmlShutdown()
        except: pass
    
    def get_val(self, key):
        try: return float(getattr(self, f"entry_{key}").get())
        except: return 0.0
    def create_tray_image(self, color_hex):
        w=64; h=64; c = color_hex.lstrip('#')
        rgb = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
        img = Image.new('RGB', (w, h), rgb)
        dc = ImageDraw.Draw(img); dc.rectangle((16, 16, 48, 48), fill="black")
        return img
    def update_tray_color(self, color_hex):
        if self.tray_icon and HAS_TRAY_LIB: self.tray_icon.icon = self.create_tray_image(color_hex)
    def minimize_to_tray(self):
        if not HAS_TRAY_LIB:
            messagebox.showerror("Fehler", "Bibliothek 'pystray' fehlt.")
            self.root.destroy(); return
        self.root.withdraw() 
        if self.tray_icon is None:
            col = COLOR_INACTIVE
            if self.is_running:
                if self.current_mode_name == "Performance": col = COLOR_UNLOCK
                elif self.current_mode_name == "3. Limit": col = COLOR_LIM3
                elif self.current_mode_name == "2. Limit": col = COLOR_LIM2
                elif self.current_mode_name == "Standard": col = COLOR_STD
            menu = pystray.Menu(pystray.MenuItem("Öffnen", self.restore_from_tray, default=True), pystray.MenuItem("Beenden", self.quit_app))
            self.tray_icon = pystray.Icon("NvidiaLimiter", self.create_tray_image(col), APP_NAME, menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
    def restore_from_tray(self, i=None, it=None): self.root.after(0, self._restore_gui)
    def _restore_gui(self):
        self.root.deiconify() 
        if self.tray_icon: self.tray_icon.stop(); self.tray_icon = None
    def quit_app(self, i=None, it=None):
        if self.tray_icon: self.tray_icon.stop()
        self.root.after(0, self.on_real_close)
    def on_window_close_attempt(self):
        if self.close_to_tray_var.get(): self.minimize_to_tray()
        else: self.on_real_close()
    def on_real_close(self):
        self.stop_event.set(); self.cleanup(); self.save_config(); self.root.destroy(); sys.exit(0)
    def add_to_listbox(self, lbox, item):
        if not item: return
        if item not in lbox.get(0, tk.END): lbox.insert(tk.END, item); self.save_config()
    def browse_file(self, target_lbox):
        fn = filedialog.askopenfilename(filetypes=[("EXE", "*.exe"), ("All", "*.*")])
        if fn: self.add_to_listbox(target_lbox, os.path.basename(fn))
    def open_process_picker(self, target_lbox):
        # FIX: Fenstergröße exakt angepasst (300x600)
        picker = tk.Toplevel(self.root); picker.geometry("300x600")
        f = ttk.Frame(picker); f.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(f); sb.pack(side="right", fill="y")
        pl = tk.Listbox(f, yscrollcommand=sb.set); pl.pack(side="left", fill="both", expand=True); sb.config(command=pl.yview)
        procs = sorted(list(set([p.info['name'] for p in psutil.process_iter(['name'])])), key=str.lower)
        for p in procs: pl.insert(tk.END, p)
        def sel(): 
            if pl.curselection(): self.add_to_listbox(target_lbox, pl.get(pl.curselection())); picker.destroy()
        ttk.Button(picker, text="Add", command=sel).pack()
    def remove_entry(self, lbox):
        if lbox.curselection(): lbox.delete(lbox.curselection()); self.save_config()
    def check_autostart_registry(self):
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            v, _ = winreg.QueryValueEx(k, "NvidiaClockLimiter")
            winreg.CloseKey(k)
            current_exe = sys.executable.replace("/", "\\") 
            if current_exe.lower() in v.lower():
                self.autostart_var.set(True)
                self.start_min_var.set("--minimized" in v)
            else:
                self.autostart_var.set(False)
        except: 
            self.autostart_var.set(False)
    def update_autostart_registry(self):
        if not self.autostart_var.get():
            try:
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
                winreg.DeleteValue(k, "NvidiaClockLimiter"); winreg.CloseKey(k)
            except: pass
        else:
            cmd = f'"{sys.executable}" --autostart' + (" --minimized" if self.start_min_var.get() else "")
            try:
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
                winreg.SetValueEx(k, "NvidiaClockLimiter", 0, winreg.REG_SZ, cmd); winreg.CloseKey(k)
            except: pass
        self.save_config()
    def load_config(self):
        # PFAD OPTIMIERUNG: Nutze den gespeicherten Pfad
        self.config_data = {}
        if os.path.exists(os.path.join(self.base_path, CONFIG_FILE)):
            try:
                with open(os.path.join(self.base_path, CONFIG_FILE), "r") as f:
                    self.config_data = json.load(f)
                    self.saved_std_core = self.config_data.get("std_core", "210")
                    self.saved_std_mem = self.config_data.get("std_mem", "405")
                    self.saved_lim2_core = self.config_data.get("lim2_core", "420")
                    self.saved_lim2_mem = self.config_data.get("lim2_mem", "810")
                    self.saved_lim3_core = self.config_data.get("lim3_core", "840")
                    self.saved_lim3_mem = self.config_data.get("lim3_mem", "7001")
                    self.list_unlock = self.config_data.get("list_unlock", [])
                    self.list_lim2 = self.config_data.get("list_lim2", [])
                    self.list_lim3 = self.config_data.get("list_lim3", [])
                    self.auto_limit_manual_var.set(self.config_data.get("auto_limit_manual", False))
                    self.auto_limit_auto_var.set(self.config_data.get("auto_limit_auto", False))
                    self.close_to_tray_var.set(self.config_data.get("close_to_tray", False))
                    self.use_dynamic_load_var.set(self.config_data.get("use_dynamic_load", False))
                    self.lang_var.set(self.config_data.get("language", "Deutsch"))
                    self.enable_lim2_var.set(self.config_data.get("enable_lim2", True))
                    self.enable_lim3_var.set(self.config_data.get("enable_lim3", True))
                    self.check_oscillation_var.set(self.config_data.get("check_oscillation", False)) # DIAGNOSE
            except: pass
    def save_config(self):
        # PFAD OPTIMIERUNG: Nutze den gespeicherten Pfad
        def ge(n): 
            try: return getattr(self, n).get()
            except: return ""
        try:
            self.list_unlock = self.lbox_unlock.get(0, tk.END)
            self.list_lim2 = self.lbox_lim2.get(0, tk.END)
            self.list_lim3 = self.lbox_lim3.get(0, tk.END)
        except: pass
        d = {
            "std_core": self.entry_std_core.get(), "std_mem": self.entry_std_mem.get(),
            "lim2_core": self.entry_lim2_core.get(), "lim2_mem": self.entry_lim2_mem.get(),
            "lim3_core": self.entry_lim3_core.get(), "lim3_mem": self.entry_lim3_mem.get(),
            "list_unlock": self.list_unlock,
            "list_lim2": self.list_lim2,
            "list_lim3": self.list_lim3,
            "auto_limit_manual": self.auto_limit_manual_var.get(),
            "auto_limit_auto": self.auto_limit_auto_var.get(),
            "close_to_tray": self.close_to_tray_var.get(),
            "use_dynamic_load": self.use_dynamic_load_var.get(),
            "sampling_rate": self.entry_rate_general.get(),
            "rate_process": self.entry_rate_process.get(), 
            "language": self.lang_var.get(),
            "enable_lim2": self.enable_lim2_var.get(),
            "enable_lim3": self.enable_lim3_var.get(),
            "check_oscillation": self.check_oscillation_var.get(),
            "unlock_act": ge("entry_unlock_act"), "unlock_act_time": ge("entry_unlock_act_time"),
            "unlock_deact": ge("entry_unlock_deact"), "unlock_deact_time": ge("entry_unlock_deact_time"),
            "lim2_act": ge("entry_lim2_act"), "lim2_act_time": ge("entry_lim2_act_time"),
            "lim2_deact": ge("entry_lim2_deact"), "lim2_deact_time": ge("entry_lim2_deact_time"),
            "lim3_act": ge("entry_lim3_act"), "lim3_act_time": ge("entry_lim3_act_time"),
            "lim3_deact": ge("entry_lim3_deact"), "lim3_deact_time": ge("entry_lim3_deact_time"),
        }
        
        self.update_runtime_cache() 
        
        try:
            with open(os.path.join(self.base_path, CONFIG_FILE), "w") as f: json.dump(d, f, indent=4)
        except: pass
    def get_gpu_name(self):
        try: 
            name = pynvml.nvmlDeviceGetName(self.nvml_handle)
            if isinstance(name, bytes): return name.decode("utf-8")
            return name
        except: return "NVIDIA GPU"
    def parse_supported_clocks(self):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            cmd = ["nvidia-smi", "-q", "-d", "SUPPORTED_CLOCKS"]
            res = subprocess.run(cmd, startupinfo=startupinfo, creationflags=0x08000000, check=True, stdout=subprocess.PIPE, text=True)
            mem_map = {}
            current_mem = None
            for line in res.stdout.splitlines():
                line = line.strip()
                if "Memory" in line and "MHz" in line:
                    parts = re.findall(r'\d+', line)
                    if parts:
                        current_mem = int(parts[0])
                        mem_map[current_mem] = []
                elif "Graphics" in line and "MHz" in line:
                    if current_mem is not None:
                        parts = re.findall(r'\d+', line)
                        if parts:
                            mem_map[current_mem].append(int(parts[0]))
            grouped_data = {}
            for mem_clk, gpu_list in mem_map.items():
                if not gpu_list: continue
                gpu_tuple = tuple(sorted(gpu_list))
                if gpu_tuple not in grouped_data: grouped_data[gpu_tuple] = []
                grouped_data[gpu_tuple].append(mem_clk)
            return grouped_data
        except: return None
    def show_hardware_info(self):
        T = self.translations[self.lang_var.get()]
        info_win = tk.Toplevel(self.root)
        info_win.title(f"Supported Clocks: {self.gpu_name}")
        info_win.geometry("700x600")
        lbl = ttk.Label(info_win, text=T["info_btn"], font=("Segoe UI", 11, "bold"))
        lbl.pack(pady=10)
        text_area = scrolledtext.ScrolledText(info_win, font=("Consolas", 9), width=80, height=25, wrap=tk.WORD)
        text_area.pack(fill="both", expand=True, padx=10, pady=10)
        info_win.config(cursor="wait"); self.root.update()
        data = self.parse_supported_clocks()
        text_area.configure(state='normal')
        if not data: text_area.insert(tk.END, "Konnte Daten nicht lesen (nvidia-smi Fehler).\n")
        else:
            sorted_items = sorted(data.items(), key=lambda item: max(item[1]), reverse=True)
            for gpu_tuple, vram_list in sorted_items:
                vrams_str = ", ".join([f"{v} MHz" for v in sorted(vram_list, reverse=True)])
                gpu_list_str = ", ".join(map(str, gpu_tuple))
                text_area.insert(tk.END, f"█ VRAM: {vrams_str}\n", "header")
                text_area.insert(tk.END, f"   GPU Core Clocks:\n")
                text_area.insert(tk.END, f"   {gpu_list_str}\n\n")
                text_area.tag_config("header", foreground=COLOR_INACTIVE, font=("Consolas", 10, "bold"))
        text_area.configure(state='disabled')
        info_win.config(cursor="")
        ttk.Button(info_win, text="Close", command=info_win.destroy).pack(pady=10)

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if __name__ == "__main__":
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join([f'"{a}"' for a in sys.argv[1:]]), None, 1)
    else:
        root = tk.Tk(); app = GpuSaverApp(root); root.mainloop()