import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import re
import psutil
try:
    from nvidia_ml_py import nvml
except ImportError:
    nvml = None
from static_ffmpeg import add_paths

CREATE_NO_WINDOW = 0x08000000

class AutoMediaValidator:
    def __init__(self, root):
        self.root = root
        self.current_lang = 'en'  # Defaulted to English
        self.is_dark_mode = True
        self.auto_close = tk.BooleanVar(value=False)
        self.use_hwaccel = tk.BooleanVar(value=False)
        
        # --- NVIDIA NVML Setup ---
        self.nvml_active = False
        if nvml:
            try:
                nvml.nvmlInit()
                self.nvml_handle = nvml.nvmlDeviceGetHandleByIndex(0)
                self.nvml_active = True
            except: pass

        self.stop_requested = False
        self.current_process = None
        self.pause_condition = threading.Condition()
        self.is_paused = False
        
        self.texts = {
            'en': {
                'title': "Auto Media Validator v1.0",
                'select_btn': "📁 Select Folder",
                'start_btn': "🚀 Start Analysis",
                'pause_btn': "⏸ Pause",
                'resume_btn': "▶ Resume",
                'stop_btn': "⏹ Stop",
                'lang_btn': "🌐 Español",
                'theme_btn': "🌓 Theme",
                'hw_accel': "CUDA Acceleration (NVIDIA)",
                'close_opt': "Auto-close when finished",
                'cpu': "CPU: ", 'gpu': "GPU: ", 'dec': "DEC: ", 'speed': "SPEED: ",
                'analyzing': "Validating ({}/{}): {}",
                'corrupt': "❌ CORRUPT: ",
                'sane': "✅ Healthy",
                'done': "Analysis finished!",
                'no_folder': "Please select a valid path."
            },
            'es': {
                'title': "Auto Media Validator v1.0",
                'select_btn': "📁 Seleccionar Carpeta",
                'start_btn': "🚀 Iniciar Análisis",
                'pause_btn': "⏸ Pausar",
                'resume_btn': "▶ Reanudar",
                'stop_btn': "⏹ Detener",
                'lang_btn': "🌐 English",
                'theme_btn': "🌓 Tema",
                'hw_accel': "Aceleración CUDA (NVIDIA)",
                'close_opt': "Cerrar al terminar",
                'cpu': "CPU: ", 'gpu': "GPU: ", 'dec': "DEC: ", 'speed': "VEL: ",
                'analyzing': "Validando ({}/{}): {}",
                'corrupt': "❌ CORRUPTO: ",
                'sane': "✅ Íntegro",
                'done': "¡Análisis completado!",
                'no_folder': "Por favor, selecciona una ruta."
            }
        }
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_ui()
        self.apply_theme()
        self.update_hardware_stats()

    def setup_ui(self):
        self.root.geometry("950x800")
        self.top_bar = tk.Frame(self.root, pady=10)
        self.top_bar.pack(fill="x")
        
        self.btn_lang = tk.Button(self.top_bar, command=self.toggle_lang, padx=10)
        self.btn_lang.pack(side="right", padx=10)
        self.btn_theme = tk.Button(self.top_bar, command=self.toggle_theme, padx=10)
        self.btn_theme.pack(side="right", padx=10)

        self.stats_frame = tk.Frame(self.root, pady=10)
        self.stats_frame.pack(fill="x", padx=20)
        self.lbl_cpu = tk.Label(self.stats_frame, font=("Consolas", 10, "bold"), fg="#4CAF50")
        self.lbl_cpu.pack(side="left", padx=15)
        self.lbl_gpu = tk.Label(self.stats_frame, font=("Consolas", 10, "bold"), fg="#FF9800")
        self.lbl_gpu.pack(side="left", padx=15)
        self.lbl_dec = tk.Label(self.stats_frame, font=("Consolas", 10, "bold"), fg="#E91E63")
        self.lbl_dec.pack(side="left", padx=15)
        self.lbl_speed = tk.Label(self.stats_frame, font=("Consolas", 10, "bold"), fg="#2196F3")
        self.lbl_speed.pack(side="right", padx=15)

        self.btn_select = tk.Button(self.root, command=self.select_folder, font=("Arial", 10))
        self.btn_select.pack(pady=5)
        self.path_label = tk.Label(self.root, font=("Arial", 9, "italic"), wraplength=800)
        self.path_label.pack()

        self.chk_hw = tk.Checkbutton(self.root, variable=self.use_hwaccel, font=("Arial", 10, "bold"))
        self.chk_hw.pack(pady=5)

        ctrl_frame = tk.Frame(self.root, pady=10)
        ctrl_frame.pack()
        self.btn_start = tk.Button(ctrl_frame, command=self.run_analysis_thread, width=12)
        self.btn_start.pack(side="left", padx=5)
        self.btn_pause = tk.Button(ctrl_frame, command=self.pause_analysis, state="disabled", width=12)
        self.btn_pause.pack(side="left", padx=5)
        self.btn_resume = tk.Button(ctrl_frame, command=self.resume_analysis, state="disabled", width=12)
        self.btn_resume.pack(side="left", padx=5)
        self.btn_stop = tk.Button(ctrl_frame, command=self.stop_analysis, state="disabled", width=12)
        self.btn_stop.pack(side="left", padx=5)

        self.chk_close = tk.Checkbutton(self.root, variable=self.auto_close)
        self.chk_close.pack()

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=850, mode="determinate")
        self.progress.pack(pady=10)

        self.log_area = scrolledtext.ScrolledText(self.root, width=115, height=25, font=("Consolas", 9))
        self.log_area.pack(pady=10)
        
        self.folder_path = ""
        self.extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.mpg', '.mpeg')
        self.update_labels()

    def update_hardware_stats(self):
        cpu = psutil.cpu_percent()
        t = self.texts[self.current_lang]
        self.lbl_cpu.config(text=f"{t['cpu']}{cpu}%")
        if self.nvml_active:
            try:
                util = nvml.nvmlDeviceGetUtilizationRates(self.nvml_handle)
                dec_util = nvml.nvmlDeviceGetDecoderUtilization(self.nvml_handle)[0]
                self.lbl_gpu.config(text=f"{t['gpu']}{util.gpu}%")
                self.lbl_dec.config(text=f"{t['dec']}{dec_util}%")
            except: pass
        self.root.after(1000, self.update_hardware_stats)

    def apply_theme(self):
        bg = "#121212" if self.is_dark_mode else "#f0f0f0"
        fg = "#ffffff" if self.is_dark_mode else "#000000"
        self.root.config(bg=bg)
        self.top_bar.config(bg=bg); self.stats_frame.config(bg=bg)
        sc = "#333333" if self.is_dark_mode else "#ffffff"
        self.chk_hw.config(bg=bg, fg=fg, selectcolor=sc, activebackground=bg)
        self.chk_close.config(bg=bg, fg=fg, selectcolor=sc, activebackground=bg)
        self.path_label.config(bg=bg, fg=fg)
        self.log_area.config(bg="#000000" if self.is_dark_mode else "#ffffff", fg=fg)

    def toggle_lang(self): self.current_lang = 'en' if self.current_lang == 'es' else 'es'; self.update_labels()
    def toggle_theme(self): self.is_dark_mode = not self.is_dark_mode; self.apply_theme()

    def update_labels(self):
        t = self.texts[self.current_lang]
        self.root.title(t['title'])
        self.btn_select.config(text=t['select_btn'])
        self.btn_start.config(text=t['start_btn'], bg="#2196F3", fg="white")
        self.btn_stop.config(text=t['stop_btn'], bg="#f44336", fg="white")
        self.btn_pause.config(text=t['pause_btn']); self.btn_resume.config(text=t['resume_btn'])
        self.btn_lang.config(text=t['lang_btn']); self.btn_theme.config(text=t['theme_btn'])
        self.chk_hw.config(text=t['hw_accel']); self.chk_close.config(text=t['close_opt'])

    def select_folder(self):
        p = filedialog.askdirectory()
        if p: self.folder_path = os.path.normpath(p); self.path_label.config(text=self.folder_path); self.btn_start.config(state="normal")

    def stop_analysis(self):
        self.stop_requested = True
        if self.current_process:
            try: self.current_process.kill()
            except: pass
        self.resume_analysis()

    def pause_analysis(self): self.is_paused = True; self.btn_pause.config(state="disabled"); self.btn_resume.config(state="normal")
    def resume_analysis(self):
        with self.pause_condition: self.is_paused = False; self.pause_condition.notify_all()
        self.btn_pause.config(state="normal"); self.btn_resume.config(state="disabled")

    def run_analysis_thread(self):
        self.stop_requested = False; self.is_paused = False
        threading.Thread(target=self.start_analysis, daemon=True).start()

    def start_analysis(self):
        t = self.texts[self.current_lang]
        self.btn_start.config(state="disabled"); self.btn_pause.config(state="normal"); self.btn_stop.config(state="normal")
        try: add_paths()
        except: pass

        files = []
        for r, d, f in os.walk(self.folder_path):
            for file in f:
                if file.lower().endswith(self.extensions): files.append(os.path.join(r, file))
        
        self.progress["maximum"] = len(files)
        for i, fpath in enumerate(files):
            with self.pause_condition:
                while self.is_paused: self.pause_condition.wait()
            if self.stop_requested: break

            self.log_area.insert(tk.END, t['analyzing'].format(i+1, len(files), os.path.basename(fpath)) + "\n")
            self.log_area.see(tk.END)

            cmd = ['ffmpeg']
            if self.use_hwaccel.get(): cmd += ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda']
            cmd += ['-v', 'error', '-stats', '-i', fpath, '-f', 'null', '-']

            self.current_process = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW, bufsize=1)
            
            buf = ""
            while True:
                c = self.current_process.stderr.read(1)
                if not c and self.current_process.poll() is not None: break
                if c in ['\r', '\n']:
                    if "speed=" in buf:
                        m = re.search(r'speed=\s*(\d+\.?\d*x)', buf)
                        if m: self.lbl_speed.config(text=f"{t['speed']}{m.group(1)}")
                    buf = ""
                else: buf += c

            if self.current_process.returncode != 0 and not self.stop_requested:
                self.log_area.insert(tk.END, f"{t['corrupt']}{os.path.basename(fpath)}\n", "error")
            elif not self.stop_requested:
                self.log_area.insert(tk.END, f"{t['sane']}\n")

            self.progress["value"] = i + 1
            self.root.update_idletasks()

        self.btn_start.config(state="normal"); self.btn_stop.config(state="disabled")
        if not self.stop_requested: messagebox.showinfo("Auto Media Validator", t['done'])

    def on_closing(self):
        self.stop_requested = True
        if self.current_process:
            try: self.current_process.kill()
            except: pass
        if self.nvml_active: nvmlShutdown()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk(); app = AutoMediaValidator(root); root.mainloop()