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
VERSION = "1.0.10" # Bugfix: Autostart-Haken prüft nun, ob der Pfad in der Registry korrekt ist

COLOR_INACTIVE = "#007acc"
COLOR_STD      = "#76b900"
COLOR_LIM2     = "#FFC400"
COLOR_LIM3     = "#FF6600"
COLOR_UNLOCK   = "#FF0000"
COLOR_DISABLED = "#555555"

class GpuSaverApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1250x950")
        self.root.resizable(False, False)
        
        self.is_running = False
        self.current_mode_name = "Unknown" 
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self.last_state_change_time = time.time()

        # Diagnose Variablen
        self.check_oscillation_var = tk.BooleanVar(value=False)
        self.state_change_history = deque(maxlen=6) 
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
        
        # Alle Checkboxen default auf FALSE
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
                "rate": "| Abtastrate (ms):",
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
                "msg_osc_text": "Achtung: Es wurde ein ständiger Wechsel zwischen Profilen erkannt!\n\nDas Programm wechselt sehr schnell hin und her (Teufelskreislauf).\n\nEmpfehlung:\n1. Erhöhen Sie die 'Zeit (ms)' bei Deaktivieren.\n2. Oder senken Sie die %-Grenze bei Deaktivieren.\n\n(Warnung pausiert für 60s)"
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
                "rate": "| Sampling Rate (ms):",
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
                "msg_osc_text": "Warning: Rapid cycling between profiles detected!\n\nThe program is switching back and forth very quickly.\n\nRecommendation:\n1. Increase 'Time (ms)' for Deactivation.\n2. Or lower the % threshold for Deactivation.\n\n(Warning paused for 60s)"
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

        if hasattr(self, 'first_load'): pass
        else:
            self.first_load = True
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

    def on_lim2_check(self):
        self.save_config()
        self.load_config()
        if not self.enable_lim2_var.get():
            self.enable_lim3_var.set(False)
            self.save_config(); self.load_config()
        self.setup_gui() 

    def on_lim3_check(self):
        self.save_config()
        self.load_config()
        if self.enable_lim3_var.get():
            self.enable_lim2_var.set(True)
            self.save_config(); self.load_config()
        self.setup_gui()

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
        ttk.Checkbutton(r3, text=T["osc_warn"], variable=self.check_oscillation_var, command=self.save_config).pack(side="left", padx=(0, 15))

        ttk.Label(r3, text=T["rate"]).pack(side="left", padx=(10, 5))
        self.entry_sampling_rate = ttk.Entry(r3, width=6)
        self.entry_sampling_rate.insert(0, self.config_data.get("sampling_rate", "500"))
        self.entry_sampling_rate.pack(side="left")
        ttk.Button(opts_frame_bottom, text=T["info_btn"], command=self.show_hardware_info).pack(side="right", padx=5, pady=5)

        # UNTEN
        settings_container = ttk.Frame(self.root)
        settings_container.pack(padx=10, pady=10, fill="x")

        # STANDARD
        frame_std = ttk.LabelFrame(settings_container, text=T["std_lim"], style="Green.TLabelframe")
        frame_std.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.create_entry_pair(frame_std, "std", self.saved_std_core, self.saved_std_mem, True)

        # LIMIT 2
        st2 = "Yellow.TLabelframe" if self.enable_lim2_var.get() else "Gray.TLabelframe"
        frame_lim2 = ttk.LabelFrame(settings_container, text=T["lim2"], style=st2)
        frame_lim2.pack(side="left", fill="both", expand=True, padx=5)
        chk2 = ttk.Checkbutton(frame_lim2, text=T["enable_prof"], variable=self.enable_lim2_var, command=self.on_lim2_check)
        chk2.grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
        self.create_entry_pair(frame_lim2, "lim2", self.saved_lim2_core, self.saved_lim2_mem, self.enable_lim2_var.get(), start_row=1)

        # LIMIT 3
        st3 = "Orange.TLabelframe" if self.enable_lim3_var.get() else "Gray.TLabelframe"
        frame_lim3 = ttk.LabelFrame(settings_container, text=T["lim3"], style=st3)
        frame_lim3.pack(side="left", fill="both", expand=True, padx=(5, 0))
        chk3 = ttk.Checkbutton(frame_lim3, text=T["enable_prof"], variable=self.enable_lim3_var, command=self.on_lim3_check)
        chk3.grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
        self.create_entry_pair(frame_lim3, "lim3", self.saved_lim3_core, self.saved_lim3_mem, self.enable_lim3_var.get(), start_row=1)

        # LISTEN
        lists_container = ttk.Frame(self.root)
        lists_container.pack(padx=10, pady=5, fill="both", expand=True)

        f1 = ttk.Frame(lists_container); f1.pack(side="left", fill="both", expand=True, padx=(0,5))
        self.build_list_ui(f1, T["unlock_list"], self.list_unlock, "unlock", True)
        self.build_load_ui(f1, "unlock", "GPU", True)

        f2 = ttk.Frame(lists_container); f2.pack(side="left", fill="both", expand=True, padx=5)
        en2 = self.enable_lim2_var.get()
        self.build_list_ui(f2, T["lim2_list"], self.list_lim2, "lim2", en2)
        self.build_load_ui(f2, "lim2", "VID", en2)

        f3 = ttk.Frame(lists_container); f3.pack(side="left", fill="both", expand=True, padx=(5,0))
        en3 = self.enable_lim3_var.get()
        self.build_list_ui(f3, T["lim3_list"], self.list_lim3, "lim3", en3)
        self.build_load_ui(f3, "lim3", "VID", en3)

        ctrl_frame = ttk.Frame(self.root)
        ctrl_frame.pack(padx=15, pady=15, fill="x")
        self.status_label = tk.Label(ctrl_frame, text=T["status_off"], fg=COLOR_INACTIVE, font=("Segoe UI", 10, "bold"))
        self.status_label.pack(side="top", pady=(0, 5))
        
        btn_txt = T["btn_stop"] if self.is_running else T["btn_start"]
        self.btn_start = ttk.Button(ctrl_frame, text=btn_txt, command=self.toggle_monitoring)
        self.btn_start.pack(fill="x", ipady=8)

        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close_attempt)

    def create_entry_pair(self, parent, key, def_c, def_m, enabled, start_row=0):
        e_c = ttk.Entry(parent, width=8)
        e_c.insert(0, def_c) 
        e_m = ttk.Entry(parent, width=8)
        e_m.insert(0, def_m)
        if not enabled:
            e_c.config(state='disabled')
            e_m.config(state='disabled')
        ttk.Label(parent, text="Core:").grid(row=start_row, column=0, padx=5, pady=5)
        e_c.grid(row=start_row, column=1, padx=5, pady=5)
        ttk.Label(parent, text="VRAM:").grid(row=start_row+1, column=0, padx=5, pady=5)
        e_m.grid(row=start_row+1, column=1, padx=5, pady=5)
        setattr(self, f"entry_{key}_core", e_c)
        setattr(self, f"entry_{key}_mem", e_m)

    def build_list_ui(self, parent, title, source, ltype, enabled):
        T = self.translations[self.lang_var.get()]
        style_name = "Bold.TLabelframe"
        if not enabled: style_name = "Gray.TLabelframe"
        elif ltype == "unlock": style_name = "Red.TLabelframe"
        elif ltype == "lim3": style_name = "Orange.TLabelframe"
        elif ltype == "lim2": style_name = "Yellow.TLabelframe"

        c = ttk.LabelFrame(parent, text=title, style=style_name)
        c.pack(fill="both", expand=True)
        lf = ttk.Frame(c); lf.pack(fill="both", expand=True, padx=5, pady=5)
        sc = ttk.Scrollbar(lf); sc.pack(side="right", fill="y")
        lb = tk.Listbox(lf, height=6, yscrollcommand=sc.set, font=("Consolas", 9))
        if not enabled: lb.config(bg="#f0f0f0", fg="#888888")
        lb.pack(side="left", fill="both", expand=True); sc.config(command=lb.yview)
        for x in source: lb.insert(tk.END, x)
        
        if ltype=="unlock": self.lbox_unlock = lb
        elif ltype=="lim2": self.lbox_lim2 = lb
        elif ltype=="lim3": self.lbox_lim3 = lb
        
        st = "normal" if enabled else "disabled"
        tf = ttk.Frame(c); tf.pack(fill="x", padx=5, pady=5)
        ttk.Button(tf, text=T["btn_browse"], state=st, command=lambda: self.browse_file(lb)).pack(side="left", fill="x", expand=True)
        ttk.Button(tf, text=T["btn_proc"], state=st, command=lambda: self.open_process_picker(lb)).pack(side="left", fill="x", expand=True)
        ttk.Button(c, text=T["btn_rem"], state=st, command=lambda: self.remove_entry(lb)).pack(fill="x", padx=5, pady=(0,5))

    def build_load_ui(self, parent, key, label_type, enabled):
        T = self.translations[self.lang_var.get()]
        st = "normal" if enabled else "disabled"
        f = ttk.LabelFrame(parent, text=T["load_ctrl"].format(type=label_type))
        f.pack(fill="x", pady=(5,0))
        r1 = ttk.Frame(f); r1.pack(fill="x", pady=2)
        ttk.Label(r1, text=T["act_gt"]).pack(side="left")
        e_a = ttk.Entry(r1, width=5, state=st); e_a.pack(side="left")
        ttk.Label(r1, text=T["time"]).pack(side="left")
        e_at = ttk.Entry(r1, width=6, state=st); e_at.pack(side="left")
        r2 = ttk.Frame(f); r2.pack(fill="x", pady=2)
        ttk.Label(r2, text=T["deact_lt"]).pack(side="left")
        e_d = ttk.Entry(r2, width=5, state=st); e_d.pack(side="left")
        ttk.Label(r2, text=T["time"]).pack(side="left")
        e_dt = ttk.Entry(r2, width=6, state=st); e_dt.pack(side="left")
        
        setattr(self, f"entry_{key}_act", e_a); setattr(self, f"entry_{key}_act_time", e_at)
        setattr(self, f"entry_{key}_deact", e_d); setattr(self, f"entry_{key}_deact_time", e_dt)
        
        def sv(e, v): 
            e.config(state="normal")
            e.delete(0, tk.END); e.insert(0, str(v))
            if not enabled: e.config(state="disabled")
        
        sv(e_a, self.config_data.get(f"{key}_act", "90"))
        sv(e_at, self.config_data.get(f"{key}_act_time", "1000"))
        sv(e_d, self.config_data.get(f"{key}_deact", "30"))
        sv(e_dt, self.config_data.get(f"{key}_deact_time", "3000"))

    # --- DIAGNOSE FUNKTION ---
    def check_for_oscillation(self):
        if len(self.state_change_history) < 5: return

        history = list(self.state_change_history)
        fast_switches = 0
        
        for i in range(1, len(history)):
            tier_now, time_now = history[i]
            tier_prev, time_prev = history[i-1]
            time_diff = (time_now - time_prev) * 1000 # ms
            
            limit_ref = 0
            
            # ABSTIEG
            if tier_now < tier_prev:
                if tier_prev == 3: limit_ref = self.get_val("unlock_deact_time") 
                elif tier_prev == 2: limit_ref = self.get_val("lim3_deact_time")
                elif tier_prev == 1: limit_ref = self.get_val("lim2_deact_time")
            
            # AUFSTIEG
            elif tier_now > tier_prev:
                if tier_now == 3: limit_ref = self.get_val("unlock_act_time")
                elif tier_now == 2: limit_ref = self.get_val("lim3_act_time")
                elif tier_now == 1: limit_ref = self.get_val("lim2_act_time")

            threshold = limit_ref + 2000 
            
            if limit_ref > 0 and time_diff < threshold:
                fast_switches += 1

        if fast_switches >= 4:
            self.trigger_warning()

    def _show_warning_modal(self):
        T = self.translations[self.lang_var.get()]
        messagebox.showwarning(T["msg_osc_title"], T["msg_osc_text"])
        self.warning_popup_open = False 

    def trigger_warning(self):
        if self.warning_popup_open:
            return

        if time.time() < self.last_warning_time + 60:
            return

        self.last_warning_time = time.time()
        self.warning_popup_open = True 
        self.state_change_history.clear()
        
        self.root.after(0, self._show_warning_modal)

    # --- CORE LOOP ---
    def get_active_tier_below(self, current_tier):
        if current_tier == 3:
            if self.enable_lim3_var.get(): return 2 
            if self.enable_lim2_var.get(): return 1 
            return 0 
        if current_tier == 2:
            if self.enable_lim2_var.get(): return 1
            return 0 
        return 0 

    def loop(self):
        loop_cnt = 0
        while not self.stop_event.is_set():
            loop_cnt += 1
            start_t = time.time()
            c, m, p, ug, uv = self.get_gpu_status()
            self.load_history.append((start_t, ug, uv))
            while self.load_history and (start_t - self.load_history[0][0]) > 10: self.load_history.popleft()

            apps_ul = [x.lower() for x in self.lbox_unlock.get(0, tk.END)]
            apps_l3 = [x.lower() for x in self.lbox_lim3.get(0, tk.END)] if self.enable_lim3_var.get() else []
            apps_l2 = [x.lower() for x in self.lbox_lim2.get(0, tk.END)] if self.enable_lim2_var.get() else []
            
            list_tier = 0 
            for proc in psutil.process_iter(['name']):
                try:
                    pn = proc.info['name'].lower()
                    if pn in apps_ul: list_tier = 3; break
                    elif self.enable_lim3_var.get() and pn in apps_l3: list_tier = max(list_tier, 2)
                    elif self.enable_lim2_var.get() and pn in apps_l2: list_tier = max(list_tier, 1)
                except: pass

            boost_tier = 0
            if self.use_dynamic_load_var.get():
                if self.get_avg_load("gpu", self.get_val("unlock_act_time")) >= self.get_val("unlock_act"): boost_tier = 3
                if boost_tier < 3 and self.enable_lim3_var.get():
                    if self.get_avg_load("vid", self.get_val("lim3_act_time")) >= self.get_val("lim3_act"): boost_tier = max(boost_tier, 2)
                if boost_tier < 2 and self.enable_lim2_var.get():
                    if self.get_avg_load("vid", self.get_val("lim2_act_time")) >= self.get_val("lim2_act"): boost_tier = max(boost_tier, 1)

            target_tier = max(list_tier, boost_tier)
            
            # --- STATUS WECHSEL ---
            if target_tier != self.state_tier:
                # DIAGNOSE: Nur wenn Checkbox an
                if self.check_oscillation_var.get():
                    now_t = time.time()
                    self.state_change_history.append((target_tier, now_t))
                    self.check_for_oscillation()

                if target_tier > self.state_tier:
                    self.state_tier = target_tier
                    self.last_state_change_time = time.time() 

                elif target_tier < self.state_tier:
                    can_drop = False
                    now = time.time()
                    time_in_state_ms = (now - self.last_state_change_time) * 1000

                    if self.state_tier == 2 and not self.enable_lim3_var.get(): can_drop = True
                    elif self.state_tier == 1 and not self.enable_lim2_var.get(): can_drop = True
                    else:
                        if not self.use_dynamic_load_var.get(): 
                            can_drop = True 
                        else: 
                            if self.state_tier == 3:
                                req_wait = self.get_val("unlock_deact_time")
                                if time_in_state_ms >= req_wait:
                                    if self.get_avg_load("gpu", req_wait) < self.get_val("unlock_deact"): 
                                        can_drop = True
                            elif self.state_tier == 2: 
                                req_wait = self.get_val("lim3_deact_time")
                                if time_in_state_ms >= req_wait:
                                    vid_low = self.get_avg_load("vid", req_wait) < self.get_val("lim3_deact")
                                    gpu_low = self.get_avg_load("gpu", req_wait) < self.get_val("lim3_deact")
                                    if vid_low and gpu_low: can_drop = True
                            elif self.state_tier == 1: 
                                req_wait = self.get_val("lim2_deact_time")
                                if time_in_state_ms >= req_wait:
                                    vid_low = self.get_avg_load("vid", req_wait) < self.get_val("lim2_deact")
                                    gpu_low = self.get_avg_load("gpu", req_wait) < self.get_val("lim2_deact")
                                    if vid_low and gpu_low: can_drop = True
                    
                    if can_drop:
                        self.state_tier = self.get_active_tier_below(self.state_tier)
                        self.last_state_change_time = time.time() 

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
            elif final_tier != 3 and loop_cnt % 10 == 0: self.enforce_limits_smart(c_req, m_req)

            T = self.translations[self.lang_var.get()]
            self.root.after(0, lambda t=t_str, col=t_col, clk=c, mem=m, pst=p, gpu=ug, vid=uv: 
                self.status_label.config(text=f"{T['status_mode']} {t} [{pst}] | {clk}/{mem} MHz | GPU: {ug}% VID: {uv:.0f}%", fg=col))

            try:
                wait_ms = int(self.entry_sampling_rate.get())
                if wait_ms < 100: wait_ms = 100
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

            self.is_running = True; self.stop_event.clear(); self.btn_start.config(text=T["btn_stop"])
            self.monitor_thread = threading.Thread(target=self.loop, daemon=True); self.monitor_thread.start()
        else:
            self.is_running = False; self.stop_event.set(); self.btn_start.config(text=T["btn_start"])
            self.status_label.config(text=T["status_off"], fg=COLOR_INACTIVE); self.reset_limits(); self.current_mode_name = "Unknown"; self.update_tray_color(COLOR_INACTIVE); self.load_history.clear()
            self.state_change_history.clear() # Reset Diagnose

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
    def get_avg_load(self, load_type, ms_duration):
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
        picker = tk.Toplevel(self.root); picker.geometry("300x400")
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
    # --- UPDATE: Smarter Registry Check ---
    def check_autostart_registry(self):
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            v, _ = winreg.QueryValueEx(k, "NvidiaClockLimiter")
            winreg.CloseKey(k)
            
            # CHECK: Stimmt der Pfad in der Registry mit der aktuellen .exe überein?
            current_exe = sys.executable.replace("/", "\\") # Pfad-Trenner normieren
            if current_exe.lower() in v.lower():
                self.autostart_var.set(True)
                self.start_min_var.set("--minimized" in v)
            else:
                # Schlüssel existiert, zeigt aber auf eine andere Datei -> Haken AUS
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
        bp = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        self.config_data = {}
        if os.path.exists(os.path.join(bp, CONFIG_FILE)):
            try:
                with open(os.path.join(bp, CONFIG_FILE), "r") as f:
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
        bp = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
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
            "sampling_rate": self.entry_sampling_rate.get(),
            "language": self.lang_var.get(),
            "enable_lim2": self.enable_lim2_var.get(),
            "enable_lim3": self.enable_lim3_var.get(),
            "check_oscillation": self.check_oscillation_var.get(), # DIAGNOSE
            "unlock_act": ge("entry_unlock_act"), "unlock_act_time": ge("entry_unlock_act_time"),
            "unlock_deact": ge("entry_unlock_deact"), "unlock_deact_time": ge("entry_unlock_deact_time"),
            "lim2_act": ge("entry_lim2_act"), "lim2_act_time": ge("entry_lim2_act_time"),
            "lim2_deact": ge("entry_lim2_deact"), "lim2_deact_time": ge("entry_lim2_deact_time"),
            "lim3_act": ge("entry_lim3_act"), "lim3_act_time": ge("entry_lim3_act_time"),
            "lim3_deact": ge("entry_lim3_deact"), "lim3_deact_time": ge("entry_lim3_deact_time"),
        }
        try:
            with open(os.path.join(bp, CONFIG_FILE), "w") as f: json.dump(d, f, indent=4)
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