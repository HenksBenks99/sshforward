"""SSH Port Forwarder Pro - Multi-Cam & Switch

Applicazione desktop per la gestione di tunnel SSH con supporto per:
- Inoltro singolo
- Inoltro multi-camera (fino a 150 dispositivi)
- Inoltro multi-switch (fino a 20 dispositivi)

NOTE SULLA SICUREZZA DELLE CREDENZIALI:
La password SSH non deve mai essere hardcoded nel codice sorgente.
La password viene caricata in questo ordine:
  1. Variabile d'ambiente: SSH_PASSWORD
  2. File di configurazione: sshforward_config.json (nella stessa directory del .py)
  3. Se nessuno dei due è presente, il campo password rimane vuoto.

Esempio di file sshforward_config.json:
  {
    "password": "LaTuaPasswordQui",
    "host": "192.168.1.10",
    "username": "pi"
  }
"""

import customtkinter as ctk
from tkinter import messagebox
import threading
import sys
import subprocess
import os
import json
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from sshtunnel import SSHTunnelForwarder
import logging

# Configurazione logging
logging.basicConfig(level=logging.ERROR)

# Configurazione appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Nome del file di configurazione esterno (non deve essere nel sorgente)
CONFIG_FILE_NAME = "sshforward_config.json"


# ============================================================================
# CARICAMENTO CONFIGURAZIONE SICURA
# ============================================================================

def load_secure_config() -> dict:
    """Carica la configurazione da variabile d'ambiente e/o file esterno.

    Priorità:
        1. Variabile d'ambiente SSH_PASSWORD
        2. File CONFIG_FILE_NAME nella directory dello script
        3. Nessun valore (ritorna dict vuoto)

    Returns:
        Dizionario con le chiavi 'password', 'host', 'username' se trovate.
    """
    config = {}

    # 1. Variabile d'ambiente
    env_password = os.environ.get("SSH_PASSWORD")
    if env_password:
        config["password"] = env_password

    # 2. File di configurazione esterno
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, CONFIG_FILE_NAME)

    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            if isinstance(file_config, dict):
                # Il file ha priorità sulla variabile d'ambiente se esplicitamente impostato
                config.update(file_config)
        except (json.JSONDecodeError, OSError) as e:
            logging.error(f"Errore lettura file configurazione: {e}")

    return config


# ============================================================================
# COSTANTI E CONFIGURAZIONE
# ============================================================================

@dataclass
class NetworkConfig:
    """Configurazione di rete per i tunnel."""
    # Range IP per camere: 10.10.0.(100 + camera_id)
    CAMERA_BASE_IP_OFFSET: int = 100
    # Range IP per switch: 10.10.0.(230 + switch_id)
    SWITCH_BASE_IP_OFFSET: int = 230
    # Porta base locale per camere: 8000 + (camera_id - 1)
    CAMERA_BASE_LOCAL_PORT: int = 8000
    # Porta base locale per switch: 7000 + (switch_id - 1)
    SWITCH_BASE_LOCAL_PORT: int = 7000
    # Limiti validi
    MIN_CAMERA_ID: int = 1
    MAX_CAMERA_ID: int = 150
    MIN_SWITCH_ID: int = 1
    MAX_SWITCH_ID: int = 20
    # Porta remota default
    DEFAULT_DEST_PORT: int = 80


@dataclass
class SSHCredentials:
    """Credenziali SSH con valori default.

    La password viene caricata in modo sicuro da variabile d'ambiente
    SSH_PASSWORD o dal file sshforward_config.json, mai hardcoded.
    """
    host: str = ""
    port: int = 22
    username: str = "pi"
    password: str = field(default_factory=lambda: load_secure_config().get("password", ""))


@dataclass
class TunnelEndpoint:
    """Rappresenta un endpoint di tunnel."""
    remote_host: str
    remote_port: int
    local_host: str = "127.0.0.1"
    local_port: int = 0


# ============================================================================
# PARSER INPUT
# ============================================================================

class InputParser:
    """Utility per il parsing di input utente (range, liste, ecc.)."""

    @staticmethod
    def parse_id_list(input_str: str, min_val: int, max_val: int) -> List[int]:
        """Parsa una stringa contenente ID singoli e/o range.

        Args:
            input_str: Stringa input (es. "1,5,7-10,15")
            min_val: Valore minimo consentito
            max_val: Valore massimo consentito

        Returns:
            Lista di ID ordinati e unici

        Raises:
            ValueError: Se gli ID sono fuori range o il formato è invalido
        """
        if not input_str or not input_str.strip():
            raise ValueError("Input vuoto")

        ids = set()
        parts = input_str.split(",")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if "-" in part:
                # Gestione range
                sub_parts = part.split("-")
                if len(sub_parts) != 2:
                    raise ValueError(f"Formato range invalido: {part}")

                try:
                    start = int(sub_parts[0].strip())
                    end = int(sub_parts[1].strip())
                except ValueError:
                    raise ValueError(f"Valori non numerici nel range: {part}")

                if start > end:
                    raise ValueError(f"Range invalido (inizio > fine): {part}")

                ids.update(range(start, end + 1))
            else:
                # ID singolo
                try:
                    ids.add(int(part))
                except ValueError:
                    raise ValueError(f"Valore non numerico: {part}")

        # Validazione range
        result = sorted(ids)
        if not result:
            raise ValueError("Nessun ID valido specificato")

        if result[0] < min_val or result[-1] > max_val:
            raise ValueError(f"ID fuori range [{min_val}-{max_val}]: {result[0]}-{result[-1]}")

        return result


# ============================================================================
# GESTORE TUNNEL
# ============================================================================

class TunnelManager:
    """Gestisce la creazione e chiusura di tunnel SSH."""

    def __init__(self, credentials: SSHCredentials):
        self.credentials = credentials
        self.tunnels: List[SSHTunnelForwarder] = []
        self._lock = threading.Lock()

    def create_single_tunnel(
        self,
        remote_host: str,
        remote_port: int,
        local_port: int
    ) -> SSHTunnelForwarder:
        """Crea un tunnel SSH singolo.

        Args:
            remote_host: Host remoto da raggiungere
            remote_port: Porta remota
            local_port: Porta locale di bind

        Returns:
            Istanza del tunnel avviato
        """
        tunnel = SSHTunnelForwarder(
            (self.credentials.host, self.credentials.port),
            ssh_username=self.credentials.username,
            ssh_password=self.credentials.password,
            remote_bind_address=(remote_host, remote_port),
            local_bind_address=('127.0.0.1', local_port)
        )
        tunnel.start()

        with self._lock:
            self.tunnels.append(tunnel)

        return tunnel

    def create_multi_tunnel(
        self,
        endpoints: List[Tuple[Tuple[str, int], Tuple[str, int]]]
    ) -> SSHTunnelForwarder:
        """Crea un tunnel SSH multiplo con più endpoint.

        Args:
            endpoints: Lista di tuple ((remote_host, remote_port), (local_host, local_port))

        Returns:
            Istanza del tunnel avviato
        """
        remote_binds = [ep[0] for ep in endpoints]
        local_binds = [ep[1] for ep in endpoints]

        tunnel = SSHTunnelForwarder(
            (self.credentials.host, self.credentials.port),
            ssh_username=self.credentials.username,
            ssh_password=self.credentials.password,
            remote_bind_addresses=remote_binds,
            local_bind_addresses=local_binds
        )
        tunnel.start()

        with self._lock:
            self.tunnels.append(tunnel)

        return tunnel

    def close_all(self):
        """Chiude tutti i tunnel attivi."""
        with self._lock:
            for tunnel in self.tunnels:
                try:
                    tunnel.close()
                except Exception:
                    pass  # Ignora errori durante la chiusura
            self.tunnels.clear()

    @property
    def is_active(self) -> bool:
        """Verifica se ci sono tunnel attivi."""
        return len(self.tunnels) > 0


# ============================================================================
# GENERATORE ENDPOINT
# ============================================================================

class EndpointGenerator:
    """Genera configurazioni di endpoint per camere e switch."""

    def __init__(self, config: NetworkConfig = None):
        self.config = config or NetworkConfig()

    def generate_camera_endpoints(
        self,
        camera_ids: List[int],
        dest_port: int
    ) -> List[TunnelEndpoint]:
        """Genera endpoint per le camere specificate.

        Args:
            camera_ids: Lista di ID camera
            dest_port: Porta di destinazione sui dispositivi remoti

        Returns:
            Lista di TunnelEndpoint configurati
        """
        endpoints = []
        for cam_id in camera_ids:
            remote_ip = f"10.10.0.{self.config.CAMERA_BASE_IP_OFFSET + cam_id}"
            local_port = self.config.CAMERA_BASE_LOCAL_PORT + (cam_id - 1)

            endpoints.append(TunnelEndpoint(
                remote_host=remote_ip,
                remote_port=dest_port,
                local_host='127.0.0.1',
                local_port=local_port
            ))

        return endpoints

    def generate_switch_endpoints(
        self,
        switch_ids: List[int],
        dest_port: int
    ) -> List[TunnelEndpoint]:
        """Genera endpoint per gli switch specificati.

        Args:
            switch_ids: Lista di ID switch
            dest_port: Porta di destinazione sui dispositivi remoti

        Returns:
            Lista di TunnelEndpoint configurati
        """
        endpoints = []
        for sw_id in switch_ids:
            remote_ip = f"10.10.0.{self.config.SWITCH_BASE_IP_OFFSET + sw_id}"
            local_port = self.config.SWITCH_BASE_LOCAL_PORT + (sw_id - 1)

            endpoints.append(TunnelEndpoint(
                remote_host=remote_ip,
                remote_port=dest_port,
                local_host='127.0.0.1',
                local_port=local_port
            ))

        return endpoints


# ============================================================================
# APPLICAZIONE GUI
# ============================================================================

class SSHForwarderApp:
    """Applicazione principale SSH Port Forwarder."""

    def __init__(self, root):
        self.root = root
        self.root.title("SSH Port Forwarder Pro - Multi-Cam & Switch")
        self.root.geometry("520x710")
        self.root.resizable(False, False)

        # Gestione chiusura finestra
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Stato applicazione
        self.is_running = False
        self.tunnel_manager: Optional[TunnelManager] = None
        self.endpoint_generator = EndpointGenerator()

        # Configurazione UI
        self._setup_fonts()
        self._build_ui()
        self.update_ui_state()

    def _setup_fonts(self):
        """Configura i font utilizzati nell'UI."""
        self.font_title = ctk.CTkFont(family="Roboto", size=13, weight="bold")
        self.font_label = ctk.CTkFont(family="Roboto", size=12)
        self.entry_height = 26

    def _build_ui(self):
        """Costruisce l'interfaccia utente."""
        self._build_ssh_credentials_section()
        self._build_mode_selection_section()
        self._build_single_tunnel_section()
        self._build_multi_cam_section()
        self._build_switch_section()
        self._build_log_and_controls()

    def _build_ssh_credentials_section(self):
        """Sezione 1: Credenziali Server SSH."""
        self.frame_ssh = ctk.CTkFrame(self.root, corner_radius=8)
        self.frame_ssh.pack(fill="x", padx=15, pady=5)

        # Titolo e pulsante nuova finestra
        ctk.CTkLabel(
            self.frame_ssh,
            text="1. Credenziali Server SSH",
            font=self.font_title,
            text_color="#3a7ebf"
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 0))

        self.btn_new_session = ctk.CTkButton(
            self.frame_ssh,
            text="APRI NUOVA FINESTRA",
            width=140,
            height=24,
            fg_color="#1976D2",
            hover_color="#1565C0",
            font=ctk.CTkFont(weight="bold", size=11),
            command=self.open_new_instance
        )
        self.btn_new_session.grid(row=0, column=2, columnspan=2, sticky="e", padx=10, pady=(8, 0))

        # Host SSH
        ctk.CTkLabel(self.frame_ssh, text="Host SSH:", font=self.font_label).grid(
            row=1, column=0, sticky="w", padx=10, pady=2
        )
        self.ent_ssh_host = ctk.CTkEntry(self.frame_ssh, width=130, height=self.entry_height)
        self.ent_ssh_host.grid(row=1, column=1, pady=2, sticky="w")

        # Porta SSH
        ctk.CTkLabel(self.frame_ssh, text="Porta:", font=self.font_label).grid(
            row=1, column=2, sticky="w", padx=10, pady=2
        )
        self.ent_ssh_port = ctk.CTkEntry(self.frame_ssh, width=60, height=self.entry_height)
        self.ent_ssh_port.grid(row=1, column=3, pady=2, sticky="w")
        self.ent_ssh_port.insert(0, "22")

        # Username
        ctk.CTkLabel(self.frame_ssh, text="Username:", font=self.font_label).grid(
            row=2, column=0, sticky="w", padx=10, pady=(2, 8)
        )
        self.ent_ssh_user = ctk.CTkEntry(self.frame_ssh, width=130, height=self.entry_height)
        self.ent_ssh_user.grid(row=2, column=1, pady=(2, 8), sticky="w")
        self.ent_ssh_user.insert(0, "pi")

        # Password
        ctk.CTkLabel(self.frame_ssh, text="Password:", font=self.font_label).grid(
            row=2, column=2, sticky="w", padx=10, pady=(2, 8)
        )
        self.ent_ssh_pass = ctk.CTkEntry(self.frame_ssh, show="*", width=140, height=self.entry_height)
        self.ent_ssh_pass.grid(row=2, column=3, pady=(2, 8), sticky="w")

        # Avviso credenziali caricate dal file esterno
        self.lbl_cred_warning = ctk.CTkLabel(
            self.frame_ssh,
            text="",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color="#81d4fa"
        )
        self.lbl_cred_warning.grid(row=3, column=0, columnspan=4, sticky="w", padx=10, pady=(0, 8))

        # Applica i valori di default caricati in modo sicuro (env var o file config)
        self._apply_secure_defaults()

    def _apply_secure_defaults(self):
        """Popola i campi SSH con valori caricati da file/variabile d'ambiente.

        Se le credenziali sono già presenti nel file esterno, i campi vengono
        disabilitati e viene mostrato un avviso informativo. L'utente può sempre
        cancellare il file di configurazione per inserire manualmente altre credenziali.
        """
        config = load_secure_config()

        has_credentials = any(config.get(k) for k in ("host", "username", "password"))

        if "host" in config and config["host"]:
            self.ent_ssh_host.delete(0, "end")
            self.ent_ssh_host.insert(0, config["host"])

        if "username" in config and config["username"]:
            self.ent_ssh_user.delete(0, "end")
            self.ent_ssh_user.insert(0, config["username"])

        if "password" in config and config["password"]:
            self.ent_ssh_pass.delete(0, "end")
            self.ent_ssh_pass.insert(0, config["password"])

        if has_credentials:
            # Disabilita i campi e mostra l'avviso
            self.ent_ssh_host.configure(state="disabled")
            self.ent_ssh_user.configure(state="disabled")
            self.ent_ssh_pass.configure(state="disabled")
            self.lbl_cred_warning.configure(
                text="Credenziali caricate dal file di configurazione esterno."
            )

    def _build_mode_selection_section(self):
        """Sezione 2: Selezione modalità."""
        self.frame_mode = ctk.CTkFrame(self.root, corner_radius=8)
        self.frame_mode.pack(fill="x", padx=15, pady=2)

        self.mode_var = ctk.StringVar(value="single")

        self.rb_single = ctk.CTkRadioButton(
            self.frame_mode,
            text="Singolo",
            variable=self.mode_var,
            value="single",
            command=self.update_ui_state,
            font=self.font_label
        )
        self.rb_single.grid(row=0, column=0, padx=15, pady=(8, 8), sticky="w")

        self.rb_multi = ctk.CTkRadioButton(
            self.frame_mode,
            text="Multi-Cam",
            variable=self.mode_var,
            value="multi",
            command=self.update_ui_state,
            font=self.font_label
        )
        self.rb_multi.grid(row=0, column=1, padx=15, pady=(8, 8), sticky="w")

        self.rb_switch = ctk.CTkRadioButton(
            self.frame_mode,
            text="Switch Fibra",
            variable=self.mode_var,
            value="switch",
            command=self.update_ui_state,
            font=self.font_label
        )
        self.rb_switch.grid(row=0, column=2, padx=15, pady=(8, 8), sticky="w")

    def _build_single_tunnel_section(self):
        """Sezione 3A: Pannello inoltro singolo."""
        self.frame_single = ctk.CTkFrame(self.root, corner_radius=8)
        self.frame_single.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(
            self.frame_single,
            text="Configurazione Singola",
            font=self.font_title
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(5, 2))

        # IP Destinatario
        ctk.CTkLabel(self.frame_single, text="IP Dest.:", font=self.font_label).grid(
            row=1, column=0, sticky="w", padx=10, pady=2
        )
        self.ent_rem_host = ctk.CTkEntry(self.frame_single, width=130, height=self.entry_height)
        self.ent_rem_host.grid(row=1, column=1, pady=2, sticky="w")
        self.ent_rem_host.insert(0, "10.10.0.101")

        # Porta Destinatario
        ctk.CTkLabel(self.frame_single, text="Porta Dest.:", font=self.font_label).grid(
            row=1, column=2, sticky="w", padx=10, pady=2
        )
        self.ent_rem_port = ctk.CTkEntry(self.frame_single, width=60, height=self.entry_height)
        self.ent_rem_port.grid(row=1, column=3, pady=2, sticky="w")
        self.ent_rem_port.insert(0, "3001")

        # Porta Locale PC
        ctk.CTkLabel(self.frame_single, text="Porta PC:", font=self.font_label).grid(
            row=2, column=0, sticky="w", padx=10, pady=(2, 8)
        )
        self.ent_loc_port = ctk.CTkEntry(self.frame_single, width=80, height=self.entry_height)
        self.ent_loc_port.grid(row=2, column=1, pady=(2, 8), sticky="w")
        self.ent_loc_port.insert(0, "8080")

    def _build_multi_cam_section(self):
        """Sezione 3B: Pannello inoltro multiplo (CAM)."""
        self.frame_multi = ctk.CTkFrame(self.root, corner_radius=8)
        self.frame_multi.pack(fill="x", padx=15, pady=2)

        ctk.CTkLabel(
            self.frame_multi,
            text="Configurazione Multi-Cam",
            font=self.font_title
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(5, 0))

        ctk.CTkLabel(
            self.frame_multi,
            text="(es. 1-16 o 1,5,7)",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="gray"
        ).grid(row=0, column=1, sticky="w", padx=0, pady=(5, 0))

        # ID Camere
        ctk.CTkLabel(self.frame_multi, text="ID Cam:", font=self.font_label).grid(
            row=1, column=0, sticky="w", padx=10, pady=(2, 8)
        )
        self.ent_cam_count = ctk.CTkEntry(self.frame_multi, width=130, height=self.entry_height)
        self.ent_cam_count.grid(row=1, column=1, pady=(2, 8), sticky="w")
        self.ent_cam_count.insert(0, "1,5,7,8,9")

        # Porta Nativa
        ctk.CTkLabel(self.frame_multi, text="Porta Nativa:", font=self.font_label).grid(
            row=1, column=2, sticky="w", padx=10, pady=(2, 8)
        )
        self.ent_cam_dest_port = ctk.CTkEntry(self.frame_multi, width=60, height=self.entry_height)
        self.ent_cam_dest_port.grid(row=1, column=3, pady=(2, 8), sticky="w")
        self.ent_cam_dest_port.insert(0, "80")

    def _build_switch_section(self):
        """Sezione 3C: Pannello Switch Fibra."""
        self.frame_switch = ctk.CTkFrame(self.root, corner_radius=8)
        self.frame_switch.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(
            self.frame_switch,
            text="Configurazione Switch Fibra",
            font=self.font_title
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(5, 0))

        ctk.CTkLabel(
            self.frame_switch,
            text="(es. 1-20 o 1,3)",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="gray"
        ).grid(row=0, column=1, sticky="w", padx=0, pady=(5, 0))

        # ID Switch
        ctk.CTkLabel(self.frame_switch, text="ID Switch:", font=self.font_label).grid(
            row=1, column=0, sticky="w", padx=10, pady=(2, 8)
        )
        self.ent_switch_count = ctk.CTkEntry(self.frame_switch, width=130, height=self.entry_height)
        self.ent_switch_count.grid(row=1, column=1, pady=(2, 8), sticky="w")
        self.ent_switch_count.insert(0, "1-20")

        # Porta Nativa
        ctk.CTkLabel(self.frame_switch, text="Porta Nativa:", font=self.font_label).grid(
            row=1, column=2, sticky="w", padx=10, pady=(2, 8)
        )
        self.ent_switch_dest_port = ctk.CTkEntry(self.frame_switch, width=60, height=self.entry_height)
        self.ent_switch_dest_port.grid(row=1, column=3, pady=(2, 8), sticky="w")
        self.ent_switch_dest_port.insert(0, "80")

    def _build_log_and_controls(self):
        """Sezione 4: Log e controlli principali."""
        # Area log
        self.txt_log = ctk.CTkTextbox(
            self.root,
            height=75,
            font=("Consolas", 11),
            corner_radius=6,
            state="disabled"
        )
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=5)

        # Label stato
        self.lbl_status = ctk.CTkLabel(
            self.root,
            text="Stato: Disconnesso",
            text_color="#ef5350",
            font=ctk.CTkFont(weight="bold", size=12)
        )
        self.lbl_status.pack(pady=(2, 0))

        # Pulsante avvia/ferma
        self.btn_toggle = ctk.CTkButton(
            self.root,
            text="AVVIA TUNNEL",
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            font=ctk.CTkFont(weight="bold", size=14),
            height=34,
            command=self.toggle_tunnel
        )
        self.btn_toggle.pack(pady=(5, 15))

    def update_ui_state(self):
        """Aggiorna lo stato di abilitazione dei controlli in base alla modalità selezionata."""
        current_mode = self.mode_var.get()
        disabled_color = "#555555"
        active_color = "#DCE4EE"
        active_title_color = "#3a7ebf"

        def apply_state(frame, is_active):
            for child in frame.winfo_children():
                if isinstance(child, (ctk.CTkEntry, ctk.CTkButton)):
                    child.configure(state="normal" if is_active else "disabled")
                elif isinstance(child, ctk.CTkLabel):
                    testo = child.cget("text")
                    if "Configurazione" in testo:
                        child.configure(text_color=active_title_color if is_active else disabled_color)
                    elif "(es." in testo:
                        child.configure(text_color="gray" if is_active else disabled_color)
                    else:
                        child.configure(text_color=active_color if is_active else disabled_color)

        apply_state(self.frame_single, current_mode == "single")
        apply_state(self.frame_multi, current_mode == "multi")
        apply_state(self.frame_switch, current_mode == "switch")

    def log_message(self, msg: str):
        """Aggiunge un messaggio al log tramite thread-safe call."""
        self.root.after(0, self._append_to_log, msg)

    def _append_to_log(self, msg: str):
        """Appende effettivamente il messaggio al textbox log."""
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def clear_log(self):
        """Pulisce l'area di log."""
        self.txt_log.configure(state="normal")
        self.txt_log.delete("0.0", "end")
        self.txt_log.configure(state="disabled")

    def open_new_instance(self):
        """Apre una nuova istanza dell'applicazione."""
        try:
            subprocess.Popen([sys.executable, sys.argv[0]])
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire una nuova istanza:\n{str(e)}")

    def toggle_tunnel(self):
        """Avvia o ferma i tunnel in base allo stato corrente."""
        if not self.is_running:
            self.is_running = True
            self.clear_log()
            threading.Thread(target=self.start_tunnels_process, daemon=True).start()
        else:
            self.stop_all_tunnels()

    def _get_credentials(self) -> SSHCredentials:
        """Recupera le credenziali dall'UI."""
        return SSHCredentials(
            host=self.ent_ssh_host.get(),
            port=int(self.ent_ssh_port.get()),
            username=self.ent_ssh_user.get(),
            password=self.ent_ssh_pass.get()
        )

    def start_tunnels_process(self):
        """Processo principale di avvio tunnel (eseguito in thread separato)."""
        try:
            credentials = self._get_credentials()
            self.tunnel_manager = TunnelManager(credentials)

            ssh_display = f"{credentials.host}:{credentials.port}"
            self.lbl_status.configure(text="Apertura tunnel in corso...", text_color="#ffa726")
            self.log_message(f"--- Inizio connessione a {ssh_display} ---")

            current_mode = self.mode_var.get()

            if current_mode == "single":
                self._start_single_tunnel()
            elif current_mode == "multi":
                self._start_multi_cam_tunnel()
            elif current_mode == "switch":
                self._start_switch_tunnel()

            # Aggiorna pulsante
            self.btn_toggle.configure(text="FERMA TUNNEL", fg_color="#d32f2f", hover_color="#b71c1c")

        except Exception as e:
            self.is_running = False
            self.lbl_status.configure(text="Errore di connessione", text_color="#ef5350")
            self.log_message(f"[ERRORE] Impossibile avviare: {str(e)}")
            messagebox.showerror("Errore", f"Impossibile avviare i tunnel:\n{str(e)}")
            self.stop_all_tunnels()

    def _start_single_tunnel(self):
        """Avvia il tunnel in modalità singola."""
        local_port = int(self.ent_loc_port.get())
        remote_host = self.ent_rem_host.get()
        remote_port = int(self.ent_rem_port.get())

        self.tunnel_manager.create_single_tunnel(remote_host, remote_port, local_port)

        self.lbl_status.configure(
            text=f"Tunnel Singolo Attivo! localhost:{local_port}",
            text_color="#66bb6a"
        )
        self.log_message(f"[OK] Singolo: localhost:{local_port} --> {remote_host}:{remote_port}")

    def _start_multi_cam_tunnel(self):
        """Avvia il tunnel in modalità multi-camera."""
        cam_dest_port = int(self.ent_cam_dest_port.get())
        cam_input = self.ent_cam_count.get().strip()

        # Parsing IDs
        target_cams = InputParser.parse_id_list(
            cam_input,
            NetworkConfig.MIN_CAMERA_ID,
            NetworkConfig.MAX_CAMERA_ID
        )

        # Generazione endpoint
        endpoints = self.endpoint_generator.generate_camera_endpoints(target_cams, cam_dest_port)

        # Creazione tunnel
        num_cams = len(target_cams)
        self.lbl_status.configure(
            text=f"Connessione SSH in corso per {num_cams} tunnel...",
            text_color="#ffa726"
        )

        tunnel_endpoints = [
            ((ep.remote_host, ep.remote_port), (ep.local_host, ep.local_port))
            for ep in endpoints
        ]
        self.tunnel_manager.create_multi_tunnel(tunnel_endpoints)

        # Logging
        for ep in endpoints:
            cam_id = ep.local_port - NetworkConfig.CAMERA_BASE_LOCAL_PORT + 1
            self.log_message(
                f"[OK] Cam {cam_id}: localhost:{ep.local_port} --> {ep.remote_host}:{ep.remote_port}"
            )

        self.lbl_status.configure(
            text=f"{num_cams} tunnel Cam Attivi! (Singola sessione SSH)",
            text_color="#66bb6a"
        )
        self.log_message(f"--- Connessione multipla ultraveloce completata ({num_cams} tunnel) ---")

    def _start_switch_tunnel(self):
        """Avvia il tunnel in modalità switch fibra."""
        switch_dest_port = int(self.ent_switch_dest_port.get())
        switch_input = self.ent_switch_count.get().strip()

        # Parsing IDs
        target_switches = InputParser.parse_id_list(
            switch_input,
            NetworkConfig.MIN_SWITCH_ID,
            NetworkConfig.MAX_SWITCH_ID
        )

        # Generazione endpoint
        endpoints = self.endpoint_generator.generate_switch_endpoints(target_switches, switch_dest_port)

        # Creazione tunnel
        num_switches = len(target_switches)
        self.lbl_status.configure(
            text=f"Connessione SSH in corso per {num_switches} switch...",
            text_color="#ffa726"
        )

        tunnel_endpoints = [
            ((ep.remote_host, ep.remote_port), (ep.local_host, ep.local_port))
            for ep in endpoints
        ]
        self.tunnel_manager.create_multi_tunnel(tunnel_endpoints)

        # Logging
        for ep in endpoints:
            sw_id = ep.local_port - NetworkConfig.SWITCH_BASE_LOCAL_PORT + 1
            self.log_message(
                f"[OK] Switch {sw_id}: localhost:{ep.local_port} --> {ep.remote_host}:{ep.remote_port}"
            )

        self.lbl_status.configure(
            text=f"{num_switches} tunnel Switch Attivi!",
            text_color="#66bb6a"
        )
        self.log_message(f"--- Connessione multipla switch completata ({num_switches} tunnel) ---")

    def stop_all_tunnels(self):
        """Ferma tutti i tunnel attivi."""
        self.lbl_status.configure(text="Chiusura connessioni...", text_color="#ffa726")

        if self.tunnel_manager:
            self.tunnel_manager.close_all()
            self.log_message("--- Tutti i tunnel sono stati chiusi ---")

        self.is_running = False
        self.btn_toggle.configure(text="AVVIA TUNNEL", fg_color="#2e7d32", hover_color="#1b5e20")
        self.lbl_status.configure(text="Stato: Disconnesso", text_color="#ef5350")

    def on_closing(self):
        """Gestisce la chiusura dell'applicazione."""
        if not self.is_running and (not self.tunnel_manager or not self.tunnel_manager.is_active):
            self.root.destroy()
            return

        self.stop_all_tunnels()
        self.show_auto_close_notification("Forward SSH terminati con successo.\nChiusura automatica in 5 secondi...")

    def show_auto_close_notification(self, msg: str):
        """Mostra notifica di chiusura automatica."""
        popup = ctk.CTkToplevel(self.root)
        popup.title("Chiusura in corso")
        popup.geometry("380x120")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)

        # Posizionamento centrato rispetto alla finestra principale
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (380 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (120 // 2)
        popup.geometry(f"+{x}+{y}")

        lbl = ctk.CTkLabel(
            popup,
            text=msg,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#66bb6a"
        )
        lbl.pack(expand=True, padx=20, pady=20)

        self.root.after(5000, self.root.destroy)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    root = ctk.CTk()
    app = SSHForwarderApp(root)
    root.mainloop()
