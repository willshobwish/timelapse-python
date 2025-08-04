import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import os
import threading
import time
from datetime import datetime, timedelta
from PIL import Image, ImageTk
import json

class TimelapseCapture:
    def __init__(self, root):
        self.root = root
        self.root.title("Capturador de Timelapse")
        self.root.geometry("1000x800")
        
        # Variáveis de controle
        self.camera = None
        self.capturing = False
        self.capture_thread = None
        self.preview_thread = None
        self.preview_running = False
        self.save_path = ""
        self.capture_count = 0
        
        # Configurações padrão
        self.settings = {
            'camera_index': 0,
            'interval_seconds': 5,
            'duration_minutes': 60,
            'end_time': '',
            'save_path': ''
        }
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configuração da câmera
        camera_frame = ttk.LabelFrame(main_frame, text="Configuração da Câmera", padding="5")
        camera_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(camera_frame, text="Dispositivo:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(camera_frame, textvariable=self.camera_var, width=20)
        self.camera_combo.grid(row=0, column=1, padx=5)
        
        ttk.Button(camera_frame, text="Detectar Câmeras", command=self.detect_cameras).grid(row=0, column=2, padx=5)
        ttk.Button(camera_frame, text="Iniciar Preview", command=self.start_preview).grid(row=0, column=3, padx=5)
        ttk.Button(camera_frame, text="Parar Preview", command=self.stop_preview).grid(row=0, column=4, padx=5)
        
        # Preview da câmera
        preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding="5")
        preview_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.preview_label = ttk.Label(preview_frame, text="Preview da câmera aparecerá aqui")
        self.preview_label.pack()
        
        # Configurações de captura
        capture_frame = ttk.LabelFrame(main_frame, text="Configurações de Captura", padding="5")
        capture_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Intervalo
        ttk.Label(capture_frame, text="Intervalo (segundos):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.interval_var = tk.StringVar(value="5")
        ttk.Entry(capture_frame, textvariable=self.interval_var, width=10).grid(row=0, column=1, padx=5)
        
        # Modo de término
        ttk.Label(capture_frame, text="Modo de término:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.end_mode_var = tk.StringVar(value="duration")
        ttk.Radiobutton(capture_frame, text="Duração", variable=self.end_mode_var, 
                       value="duration", command=self.update_end_mode).grid(row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(capture_frame, text="Hora específica", variable=self.end_mode_var, 
                       value="time", command=self.update_end_mode).grid(row=1, column=2, sticky=tk.W)
        
        # Duração
        ttk.Label(capture_frame, text="Duração (minutos):").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.duration_var = tk.StringVar(value="60")
        self.duration_entry = ttk.Entry(capture_frame, textvariable=self.duration_var, width=10)
        self.duration_entry.grid(row=2, column=1, padx=5)
        
        # Hora específica
        ttk.Label(capture_frame, text="Hora de término (HH:MM):").grid(row=3, column=0, sticky=tk.W, padx=5)
        self.end_time_var = tk.StringVar()
        self.end_time_entry = ttk.Entry(capture_frame, textvariable=self.end_time_var, width=10)
        self.end_time_entry.grid(row=3, column=1, padx=5)
        self.end_time_entry.config(state='disabled')
        
        # Pasta de destino
        path_frame = ttk.LabelFrame(main_frame, text="Pasta de Destino", padding="5")
        path_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.path_var, width=50).grid(row=0, column=0, padx=5)
        ttk.Button(path_frame, text="Selecionar", command=self.select_save_path).grid(row=0, column=1, padx=5)
        
        # Controles de captura
        control_frame = ttk.LabelFrame(main_frame, text="Controles", padding="5")
        control_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.start_button = ttk.Button(control_frame, text="Iniciar Captura", command=self.start_capture)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="Parar Captura", command=self.stop_capture, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Status
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="5")
        status_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.status_var = tk.StringVar(value="Pronto para iniciar")
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=0, sticky=tk.W)
        
        self.progress_var = tk.StringVar(value="Imagens capturadas: 0")
        ttk.Label(status_frame, textvariable=self.progress_var).grid(row=1, column=0, sticky=tk.W)
        
        # Detectar câmeras ao iniciar
        self.root.after(100, self.detect_cameras)
        
    def detect_cameras(self):
        """Detecta câmeras disponíveis"""
        cameras = []
        for i in range(5):  # Reduzido para 5 para evitar muitos erros
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # Usa DirectShow no Windows
                if cap.isOpened():
                    # Testa se consegue ler um frame
                    ret, frame = cap.read()
                    if ret:
                        cameras.append(f"Camera {i}")
                cap.release()
            except Exception as e:
                continue
        
        if cameras:
            self.camera_combo['values'] = cameras
            self.camera_combo.current(0)
            self.status_var.set(f"Encontradas {len(cameras)} câmera(s)")
        else:
            self.status_var.set("Nenhuma câmera encontrada")
            messagebox.showwarning("Aviso", "Nenhuma câmera foi encontrada!")
    
    def start_preview(self):
        """Inicia o preview da câmera"""
        if self.preview_running:
            return
            
        camera_index = self.get_camera_index()
        if camera_index is None:
            return
            
        self.camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)  # Usa DirectShow
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        if not self.camera.isOpened():
            messagebox.showerror("Erro", "Não foi possível abrir a câmera")
            return
            
        self.preview_running = True
        self.preview_thread = threading.Thread(target=self.preview_loop)
        self.preview_thread.daemon = True
        self.preview_thread.start()
        
    def stop_preview(self):
        """Para o preview da câmera"""
        self.preview_running = False
        if self.camera:
            self.camera.release()
            self.camera = None
        self.preview_label.config(image='', text="Preview parado")
        
    def preview_loop(self):
        """Loop do preview"""
        while self.preview_running:
            if self.camera and self.camera.isOpened():
                ret, frame = self.camera.read()
                if ret:
                    # Redimensiona o frame para o preview
                    frame = cv2.resize(frame, (400, 300))
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = Image.fromarray(frame_rgb)
                    photo = ImageTk.PhotoImage(image)
                    
                    # Atualiza o preview na thread principal
                    self.root.after(0, lambda: self.update_preview(photo))
            time.sleep(0.033)  # ~30 FPS
            
    def update_preview(self, photo):
        """Atualiza a imagem do preview"""
        self.preview_label.config(image=photo, text="")
        self.preview_label.image = photo  # Mantém referência
        
    def get_camera_index(self):
        """Obtém o índice da câmera selecionada"""
        camera_text = self.camera_var.get()
        if not camera_text:
            messagebox.showwarning("Aviso", "Selecione uma câmera")
            return None
        try:
            return int(camera_text.split()[-1])
        except:
            messagebox.showerror("Erro", "Câmera inválida")
            return None
            
    def update_end_mode(self):
        """Atualiza os campos baseado no modo de término"""
        if self.end_mode_var.get() == "duration":
            self.duration_entry.config(state='normal')
            self.end_time_entry.config(state='disabled')
        else:
            self.duration_entry.config(state='disabled')
            self.end_time_entry.config(state='normal')
            
    def select_save_path(self):
        """Seleciona a pasta para salvar as imagens"""
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)
            self.save_path = path
            
    def validate_settings(self):
        """Valida as configurações antes de iniciar a captura"""
        # Verifica intervalo
        try:
            interval = float(self.interval_var.get())
            if interval <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Erro", "Intervalo deve ser um número positivo")
            return False
            
        # Verifica pasta
        if not self.save_path:
            messagebox.showerror("Erro", "Selecione uma pasta para salvar as imagens")
            return False
            
        # Verifica modo de término
        if self.end_mode_var.get() == "duration":
            try:
                duration = float(self.duration_var.get())
                if duration <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Erro", "Duração deve ser um número positivo")
                return False
        else:
            try:
                time_str = self.end_time_var.get()
                datetime.strptime(time_str, "%H:%M")
            except ValueError:
                messagebox.showerror("Erro", "Formato de hora inválido (use HH:MM)")
                return False
                
        return True
        
    def start_capture(self):
        """Inicia a captura de timelapse"""
        if not self.validate_settings():
            return
            
        camera_index = self.get_camera_index()
        if camera_index is None:
            return
            
        # Para o preview se estiver rodando
        self.stop_preview()
        
        # Cria pasta para a sessão
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_folder = os.path.join(self.save_path, f"timelapse_{timestamp}")
        os.makedirs(session_folder, exist_ok=True)
        
        self.capturing = True
        self.capture_count = 0
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        
        # Inicia thread de captura
        self.capture_thread = threading.Thread(target=self.capture_loop, args=(camera_index, session_folder))
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
    def capture_loop(self, camera_index, session_folder):
        """Loop principal de captura"""
        camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)  # Usa DirectShow
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        if not camera.isOpened():
            self.root.after(0, lambda: messagebox.showerror("Erro", "Não foi possível abrir a câmera"))
            self.root.after(0, self.stop_capture)
            return
            
        interval = float(self.interval_var.get())
        
        # Calcula quando parar
        if self.end_mode_var.get() == "duration":
            duration_minutes = float(self.duration_var.get())
            end_time = datetime.now() + timedelta(minutes=duration_minutes)
        else:
            time_str = self.end_time_var.get()
            today = datetime.now().date()
            end_time = datetime.combine(today, datetime.strptime(time_str, "%H:%M").time())
            
            # Se a hora já passou, assume que é para amanhã
            if end_time <= datetime.now():
                end_time += timedelta(days=1)
        
        self.root.after(0, lambda: self.status_var.set("Capturando..."))
        
        try:
            while self.capturing and datetime.now() < end_time:
                ret, frame = camera.read()
                if ret:
                    # Salva a imagem
                    filename = f"frame_{self.capture_count:06d}.jpg"
                    filepath = os.path.join(session_folder, filename)
                    cv2.imwrite(filepath, frame)
                    
                    self.capture_count += 1
                    
                    # Atualiza status
                    remaining = end_time - datetime.now()
                    self.root.after(0, lambda: self.progress_var.set(f"Imagens capturadas: {self.capture_count}"))
                    self.root.after(0, lambda: self.status_var.set(f"Capturando... Restam: {str(remaining).split('.')[0]}"))
                
                # Aguarda o próximo intervalo
                time.sleep(interval)
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro durante a captura: {str(e)}"))
        finally:
            camera.release()
            self.root.after(0, self.capture_finished)
            
    def capture_finished(self):
        """Chamado quando a captura termina"""
        self.capturing = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_var.set(f"Captura finalizada! Total: {self.capture_count} imagens")
        messagebox.showinfo("Concluído", f"Captura finalizada!\nTotal de imagens: {self.capture_count}")
        
    def stop_capture(self):
        """Para a captura manual"""
        self.capturing = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_var.set("Captura interrompida pelo usuário")
        
    def save_settings(self):
        """Salva as configurações"""
        self.settings = {
            'camera_index': self.get_camera_index() or 0,
            'interval_seconds': self.interval_var.get(),
            'duration_minutes': self.duration_var.get(),
            'end_time': self.end_time_var.get(),
            'save_path': self.save_path
        }
        
        try:
            with open('timelapse_settings.json', 'w') as f:
                json.dump(self.settings, f)
        except:
            pass
            
    def load_settings(self):
        """Carrega as configurações salvas"""
        try:
            with open('timelapse_settings.json', 'r') as f:
                self.settings = json.load(f)
                
            self.interval_var.set(self.settings.get('interval_seconds', '5'))
            self.duration_var.set(self.settings.get('duration_minutes', '60'))
            self.end_time_var.set(self.settings.get('end_time', ''))
            self.save_path = self.settings.get('save_path', '')
            self.path_var.set(self.save_path)
        except:
            pass
            
    def on_closing(self):
        """Chamado ao fechar a aplicação"""
        self.stop_preview()
        self.stop_capture()
        self.save_settings()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = TimelapseCapture(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()