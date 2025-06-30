import sys
import os
import subprocess
import yaml
import json
import threading
import time
import importlib
import subprocess
import pkg_resources
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QLineEdit, QCheckBox, QComboBox, QPushButton, 
                           QTabWidget, QTextEdit, QSpinBox, QDoubleSpinBox,
                           QScrollArea, QGroupBox, QFormLayout, QFileDialog,
                           QMessageBox, QSlider, QSplitter, QTreeWidget, QTreeWidgetItem,
                           QProgressDialog)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QUrl
from PyQt6.QtGui import QFont, QIcon, QDesktopServices, QColor, QPalette, QTextCursor

class LogMonitor(QThread):
    new_log_line = pyqtSignal(str)
    
    def __init__(self, log_file):
        super().__init__()
        self.log_file = log_file
        self.running = True
        
    def run(self):
        # Create the log file if it doesn't exist
        if not os.path.exists(self.log_file):
            open(self.log_file, 'w').close()
            
        with open(self.log_file, 'r') as f:
            # Move to the end of the file
            f.seek(0, 2)
            while self.running:
                line = f.readline()
                if line:
                    self.new_log_line.emit(line)
                time.sleep(0.1)
    
    def stop(self):
        self.running = False


class WorkerThread(QThread):
    update_status = pyqtSignal(str)
    job_completed = pyqtSignal(dict)
    
    def __init__(self, worker_script):
        super().__init__()
        self.worker_script = worker_script
        self.process = None
        
    def run(self):
        try:
            self.update_status.emit("Starting worker...")
            
            # Set environment variable to ensure the right Python path
            env = os.environ.copy()
            
            # Add the Python path to ensure dependencies are found
            python_path = os.path.dirname(sys.executable)
            if 'PATH' in env:
                env['PATH'] = f"{python_path}{os.pathsep}{env['PATH']}"
            else:
                env['PATH'] = python_path
                
            # Set PYTHONPATH to include the site-packages directory
            site_packages = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages')
            if os.path.exists(site_packages):
                if 'PYTHONPATH' in env:
                    env['PYTHONPATH'] = f"{site_packages}{os.pathsep}{env['PYTHONPATH']}"
                else:
                    env['PYTHONPATH'] = site_packages
            
            worker_dir = os.path.dirname(self.worker_script)
            
            # If the worker script is in a module directory, adjust the working directory
            if "horde_worker_regen" in self.worker_script:
                # Go up one level to the main package directory
                worker_dir = os.path.dirname(worker_dir)
                
            # Determine how to run the script based on file extension
            script_name = os.path.basename(self.worker_script)
            
            if sys.platform == 'win32':
                if self.worker_script.endswith('.cmd'):
                    # For Windows CMD scripts, run directly
                    self.update_status.emit(f"Starting worker using {script_name}...")
                    self.process = subprocess.Popen(
                        [self.worker_script],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        cwd=worker_dir,  # Set working directory to worker folder
                        env=env
                    )
                else:
                    # For Python scripts, create a wrapper script that handles missing dependencies
                    self.update_status.emit(f"Starting worker using Python: {script_name}...")
                    
                    # Create a temporary wrapper script that installs dependencies if needed
                    wrapper_content = f"""
import sys
import subprocess
import importlib

# Try to import required modules, install if missing
required_modules = ['loguru', 'pyyaml', 'requests', 'tqdm']
for module in required_modules:
    try:
        importlib.import_module(module)
    except ImportError:
        print(f"Installing missing dependency: {{module}}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", module])
        
# Now run the actual worker script
try:
    script_path = r"{self.worker_script}"
    sys.path.insert(0, r"{worker_dir}")
    with open(script_path) as f:
        exec(compile(f.read(), script_path, 'exec'))
except Exception as e:
    print(f"Error running worker script: {{e}}")
"""
                    
                    # Write the wrapper script to a temporary file
                    wrapper_path = os.path.join(worker_dir, "gui_worker_wrapper.py")
                    with open(wrapper_path, 'w') as f:
                        f.write(wrapper_content)
                    
                    # Run the wrapper script
                    python_executable = sys.executable
                    self.process = subprocess.Popen(
                        [python_executable, wrapper_path], 
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        cwd=worker_dir,  # Set working directory to worker folder
                        env=env
                    )
            else:
                # Linux/macOS
                if self.worker_script.endswith('.sh'):
                    # For shell scripts, use bash
                    self.update_status.emit(f"Starting worker using {script_name}...")
                    self.process = subprocess.Popen(
                        ["bash", self.worker_script], 
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        cwd=worker_dir,  # Set working directory to worker folder
                        env=env
                    )
                else:
                    # For Python scripts, create a wrapper script that handles missing dependencies
                    self.update_status.emit(f"Starting worker using Python: {script_name}...")
                    
                    # Create a temporary wrapper script that installs dependencies if needed
                    wrapper_content = f"""
import sys
import subprocess
import importlib

# Try to import required modules, install if missing
required_modules = ['loguru', 'pyyaml', 'requests', 'tqdm']
for module in required_modules:
    try:
        importlib.import_module(module)
    except ImportError:
        print(f"Installing missing dependency: {{module}}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", module])
        
# Now run the actual worker script
try:
    script_path = r"{self.worker_script}"
    sys.path.insert(0, r"{worker_dir}")
    with open(script_path) as f:
        exec(compile(f.read(), script_path, 'exec'))
except Exception as e:
    print(f"Error running worker script: {{e}}")
"""
                    
                    # Write the wrapper script to a temporary file
                    wrapper_path = os.path.join(worker_dir, "gui_worker_wrapper.py")
                    with open(wrapper_path, 'w') as f:
                        f.write(wrapper_content)
                    
                    # Run the wrapper script
                    python_executable = sys.executable
                    self.process = subprocess.Popen(
                        [python_executable, wrapper_path], 
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        cwd=worker_dir,  # Set working directory to worker folder
                        env=env
                    )
            
            self.update_status.emit("Worker running")
            
            # Read output and parse job information
            for line in iter(self.process.stdout.readline, ''):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                    
                # Always emit the status update for logging
                self.update_status.emit(line)
                
                # Parse important status messages and format them appropriately
                if "Job completed" in line or "Kudos earned" in line:
                    # Parse job completion information
                    job_info = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "details": line}
                    self.job_completed.emit(job_info)
                    
                # Track other important worker states
                elif "Waiting for" in line and "jobs" in line:
                    self.update_status.emit("Worker is online and waiting for jobs")
                    
                elif "Starting worker" in line or "Initializing" in line:
                    self.update_status.emit("Worker initialization in progress")
                    
                elif "error" in line.lower() or "exception" in line.lower() or "ERROR" in line:
                    # Error occurred - highlight these clearly
                    self.update_status.emit(f"⚠️ ERROR: {line}")
                    
                elif "WARNING" in line or "warning" in line.lower():
                    # Warning message
                    self.update_status.emit(f"⚠️ WARNING: {line}")
                    
                elif "INFO" in line:
                    # Info message - pass through normally
                    pass
                    
                elif "Loading model" in line:
                    # Model loading information
                    self.update_status.emit(f"🔄 Loading model: {line}")
                    
                elif "kudos" in line.lower():
                    # Kudos related information
                    self.update_status.emit(f"💰 {line}")
                    
                elif "maintenance mode" in line.lower():
                    # Maintenance mode warning
                    self.update_status.emit(f"⚠️ MAINTENANCE: {line}")
                    
                elif "downloaded" in line.lower() and "model" in line.lower():
                    # Model download information
                    self.update_status.emit(f"📥 {line}")
                    
                elif "Finished generating" in line:
                    # Generation complete
                    self.update_status.emit(f"✅ {line}")
                    self.job_completed.emit(job_info)
                
                # Check for other important messages
                if "Waiting for jobs" in line:
                    self.update_status.emit("Worker is online and waiting for jobs")
                
                # Flush stdout to ensure we get output in real-time
                sys.stdout.flush()
            
            self.update_status.emit("Worker process ended")
        except Exception as e:
            self.update_status.emit(f"Error: {str(e)}")
    
    def stop(self):
        if self.process:
            if sys.platform == 'win32':
                # On Windows, we send Ctrl+C signal
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)])
            else:
                # On Unix, we can use terminate
                self.process.terminate()


class HordeWorkerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("AI Horde Worker reGen - GUI")
        self.setMinimumSize(1200, 800)
        
        # Initialize variables
        self.worker_thread = None
        self.log_monitor = None
        self.config_file = None
        self.config_data = {}
        self.worker_running = False
        self.kudos_earned = 0
        self.jobs_completed = 0
        
        # Set up UI
        self.setup_ui()
        
        # Try to load saved settings from previous sessions
        self.load_saved_settings()
        
        # If no saved settings, check for horde-worker-reGen installation
        if not self.config_file:
            self.check_installation()
            
        # Try to load configuration
        self.load_default_config()
        
        # Set up timers for stats updates
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(5000)  # Update every 5 seconds
        
    def load_saved_settings(self):
        """Load previously saved GUI settings"""
        settings_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings")
        settings_file = os.path.join(settings_dir, "gui_settings.json")
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                
                if 'worker_folder' in settings and os.path.exists(settings['worker_folder']):
                    self.folder_path.setText(settings['worker_folder'])
                    
                if 'config_file' in settings and os.path.exists(settings['config_file']):
                    self.config_file = settings['config_file']
                    self.append_log(f"Loaded previous settings. Config file: {self.config_file}")
            except Exception as e:
                print(f"Warning: Could not load settings: {e}")
    
    def setup_ui(self):
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create top bar with status indicators
        status_bar = QHBoxLayout()
        
        # Worker status indicator
        self.status_label = QLabel("Status: Not Running")
        self.status_label.setStyleSheet("font-weight: bold; color: #d9534f;")
        status_bar.addWidget(self.status_label)
        
        status_bar.addStretch()
        
        # Kudos info
        self.kudos_label = QLabel("Kudos Earned: 0")
        status_bar.addWidget(self.kudos_label)
        
        # Jobs info
        self.jobs_label = QLabel("Jobs Completed: 0")
        status_bar.addWidget(self.jobs_label)
        
        main_layout.addLayout(status_bar)
        
        # Create tab widget for different sections
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Add tabs
        self.setup_dashboard_tab()
        self.setup_config_tab()
        self.setup_logs_tab()
        self.setup_models_tab()
        self.setup_about_tab()
        
        # Add buttons at bottom
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Start Worker")
        self.run_button.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold; padding: 8px 16px;")
        self.run_button.clicked.connect(self.toggle_worker)
        button_layout.addWidget(self.run_button)
        
        self.save_config_button = QPushButton("Save Configuration")
        self.save_config_button.setStyleSheet("background-color: #428bca; color: white; font-weight: bold; padding: 8px 16px;")
        self.save_config_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_config_button)
        
        main_layout.addLayout(button_layout)
    
    def setup_dashboard_tab(self):
        dashboard_widget = QWidget()
        layout = QVBoxLayout(dashboard_widget)
        
        # Quick stats
        stats_group = QGroupBox("Worker Statistics")
        stats_layout = QFormLayout()
        
        self.uptime_label = QLabel("00:00:00")
        stats_layout.addRow("Uptime:", self.uptime_label)
        
        self.current_job_label = QLabel("None")
        stats_layout.addRow("Current Job:", self.current_job_label)
        
        self.kudos_rate_label = QLabel("0 / hour")
        stats_layout.addRow("Kudos Rate:", self.kudos_rate_label)
        
        self.models_loaded_label = QLabel("0")
        stats_layout.addRow("Models Loaded:", self.models_loaded_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Recent jobs
        jobs_group = QGroupBox("Recent Jobs")
        jobs_layout = QVBoxLayout()
        
        self.jobs_text = QTextEdit()
        self.jobs_text.setReadOnly(True)
        jobs_layout.addWidget(self.jobs_text)
        
        jobs_group.setLayout(jobs_layout)
        layout.addWidget(jobs_group)
        
        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout()
        
        update_worker_btn = QPushButton("Update Worker")
        update_worker_btn.clicked.connect(self.update_worker)
        actions_layout.addWidget(update_worker_btn)
        
        update_runtime_btn = QPushButton("Update Runtime")
        update_runtime_btn.clicked.connect(self.update_runtime)
        actions_layout.addWidget(update_runtime_btn)
        
        open_logs_btn = QPushButton("Open Logs Folder")
        open_logs_btn.clicked.connect(self.open_logs_folder)
        actions_layout.addWidget(open_logs_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        self.tabs.addTab(dashboard_widget, "Dashboard")
    
    def setup_config_tab(self):
        config_widget = QScrollArea()
        config_widget.setWidgetResizable(True)
        
        config_content = QWidget()
        layout = QVBoxLayout(config_content)
        
        # Worker folder location
        folder_group = QGroupBox("Worker Location")
        folder_layout = QHBoxLayout()
        
        self.folder_path = QLineEdit()
        folder_layout.addWidget(self.folder_path)
        
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_worker_folder)
        folder_layout.addWidget(browse_button)
        
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)
        
        # Basic settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        basic_layout.addRow("API Key:", self.api_key_input)
        
        self.worker_name_input = QLineEdit()
        basic_layout.addRow("Worker Name:", self.worker_name_input)
        
        # Priority models to load
        self.models_input = QTextEdit()
        self.models_input.setMaximumHeight(100)
        basic_layout.addRow("Models to Load:", self.models_input)
        
        # NSFW toggle
        self.nsfw_checkbox = QCheckBox("Allow NSFW Content")
        basic_layout.addRow("", self.nsfw_checkbox)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # Performance settings
        perf_group = QGroupBox("Performance Settings")
        perf_layout = QFormLayout()
        
        self.max_threads_spin = QSpinBox()
        self.max_threads_spin.setRange(1, 8)
        self.max_threads_spin.setValue(1)
        perf_layout.addRow("Max Threads:", self.max_threads_spin)
        
        self.max_power_spin = QSpinBox()
        self.max_power_spin.setRange(8, 128)
        self.max_power_spin.setValue(32)
        perf_layout.addRow("Max Power:", self.max_power_spin)
        
        self.queue_size_spin = QSpinBox()
        self.queue_size_spin.setRange(0, 4)
        self.queue_size_spin.setValue(1)
        perf_layout.addRow("Queue Size:", self.queue_size_spin)
        
        self.safety_on_gpu_checkbox = QCheckBox()
        perf_layout.addRow("Safety on GPU:", self.safety_on_gpu_checkbox)
        
        self.high_memory_mode_checkbox = QCheckBox()
        perf_layout.addRow("High Memory Mode:", self.high_memory_mode_checkbox)
        
        self.max_batch_spin = QSpinBox()
        self.max_batch_spin.setRange(1, 16)
        self.max_batch_spin.setValue(4)
        perf_layout.addRow("Max Batch Size:", self.max_batch_spin)
        
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        # Feature settings
        feature_group = QGroupBox("Feature Settings")
        feature_layout = QFormLayout()
        
        self.allow_lora_checkbox = QCheckBox()
        feature_layout.addRow("Allow LoRA:", self.allow_lora_checkbox)
        
        self.allow_controlnet_checkbox = QCheckBox()
        feature_layout.addRow("Allow ControlNet:", self.allow_controlnet_checkbox)
        
        self.allow_sdxl_controlnet_checkbox = QCheckBox()
        feature_layout.addRow("Allow SDXL ControlNet:", self.allow_sdxl_controlnet_checkbox)
        
        self.allow_post_processing_checkbox = QCheckBox()
        feature_layout.addRow("Allow Post-Processing:", self.allow_post_processing_checkbox)
        
        feature_group.setLayout(feature_layout)
        layout.addWidget(feature_group)
        
        # Models to skip
        models_skip_group = QGroupBox("Models to Skip")
        models_skip_layout = QVBoxLayout()
        
        self.models_skip_input = QTextEdit()
        self.models_skip_input.setMaximumHeight(100)
        models_skip_layout.addWidget(self.models_skip_input)
        
        models_skip_group.setLayout(models_skip_layout)
        layout.addWidget(models_skip_group)
        
        config_widget.setWidget(config_content)
        self.tabs.addTab(config_widget, "Configuration")
    
    def setup_logs_tab(self):
        logs_widget = QWidget()
        layout = QVBoxLayout(logs_widget)
        
        # Create log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_display.setFont(QFont("Courier New", 9))
        layout.addWidget(self.log_display)
        
        # Add log controls
        log_controls = QHBoxLayout()
        
        # Update log file options based on README information
        self.log_file_combo = QComboBox()
        self.log_file_combo.addItems([
            "Direct Output",  # Our new direct capture option
            "bridge.log",     # Main window log
            "bridge_1.log",   # Process 1 log
            "bridge_2.log",   # Process 2 log (if applicable)
            "trace.log",      # Main errors/warnings log
            "trace_1.log",    # Process 1 errors/warnings
            "trace_2.log"     # Process 2 errors/warnings (if applicable)
        ])
        self.log_file_combo.setCurrentText("Direct Output")
        self.log_file_combo.currentTextChanged.connect(self.change_log_file)
        log_controls.addWidget(QLabel("Log Source:"))
        log_controls.addWidget(self.log_file_combo)
        
        # Add button to open logs folder
        open_logs_btn = QPushButton("Open Logs Folder")
        open_logs_btn.clicked.connect(self.open_logs_folder)
        log_controls.addWidget(open_logs_btn)
        
        clear_log_btn = QPushButton("Clear Display")
        clear_log_btn.clicked.connect(self.log_display.clear)
        log_controls.addWidget(clear_log_btn)
        
        auto_scroll_check = QCheckBox("Auto-scroll")
        auto_scroll_check.setChecked(True)
        log_controls.addWidget(auto_scroll_check)
        
        layout.addLayout(log_controls)
        
        # Add explanation about logs
        log_info = QLabel(
            "Logs: 'bridge*.log' files contain all information. 'trace*.log' files contain errors and warnings only.\n"
            "Direct Output shows the real-time output from the worker process."
        )
        log_info.setWordWrap(True)
        log_info.setStyleSheet("font-style: italic; color: #666;")
        layout.addWidget(log_info)
        
        self.tabs.addTab(logs_widget, "Logs")
    
    def setup_models_tab(self):
        models_widget = QWidget()
        layout = QVBoxLayout(models_widget)
        
        # Model management controls
        controls_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Model List")
        refresh_btn.clicked.connect(self.refresh_model_list)
        controls_layout.addWidget(refresh_btn)
        
        add_custom_btn = QPushButton("Add Custom Model")
        add_custom_btn.clicked.connect(self.add_custom_model)
        controls_layout.addWidget(add_custom_btn)
        
        layout.addLayout(controls_layout)
        
        # Model list
        self.model_tree = QTreeWidget()
        self.model_tree.setHeaderLabels(["Model", "Type", "Status", "Size"])
        self.model_tree.setColumnWidth(0, 300)
        layout.addWidget(self.model_tree)
        
        self.tabs.addTab(models_widget, "Models")
    
    def setup_about_tab(self):
        about_widget = QWidget()
        layout = QVBoxLayout(about_widget)
        
        # Title and info
        title_label = QLabel("AI Horde Worker reGen - GUI")
        title_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        desc_label = QLabel(
            "A PyQt6 graphical interface for the AI Horde Worker reGen project.\n"
            "This GUI helps you manage and monitor your worker contribution to the AI Horde network."
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Links
        links_group = QGroupBox("Useful Links")
        links_layout = QVBoxLayout()
        
        horde_link = QPushButton("AI Horde Website")
        horde_link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://aihorde.net/")))
        links_layout.addWidget(horde_link)
        
        github_link = QPushButton("GitHub Repository")
        github_link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/Haidra-Org/horde-worker-reGen")))
        links_layout.addWidget(github_link)
        
        discord_link = QPushButton("Discord Community")
        discord_link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://discord.gg/3DxrhksKzn")))
        links_layout.addWidget(discord_link)
        
        links_group.setLayout(links_layout)
        layout.addWidget(links_group)
        
        # Disclaimer
        disclaimer = QLabel(
            "This GUI is an unofficial third-party tool. Please follow AI Horde's terms of service "
            "and guidelines when using this worker. Review the license information in the repository."
        )
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet("font-style: italic; color: #666;")
        layout.addWidget(disclaimer)
        
        layout.addStretch()
        
        self.tabs.addTab(about_widget, "About")
    
    def check_installation(self):
        """Check for horde-worker-reGen installation in common locations"""
        potential_paths = []
        
        if sys.platform == 'win32':
            # Common Windows locations
            potential_paths = [
                os.path.expanduser("~/horde-worker-reGen"),
                os.path.expanduser("~/Downloads/horde-worker-reGen"),
                "C:/horde-worker-reGen",
                "D:/horde-worker-reGen",
                os.path.expanduser("~/horde-worker-reGen-main"),
            ]
        else:
            # Linux/macOS locations
            potential_paths = [
                os.path.expanduser("~/horde-worker-reGen"),
                os.path.expanduser("~/Downloads/horde-worker-reGen"),
                os.path.expanduser("~/projects/horde-worker-reGen"),
                "/opt/horde-worker-reGen",
                os.path.expanduser("~/horde-worker-reGen-main"),
            ]
        
        # Try to find the installation
        for path in potential_paths:
            if os.path.exists(path):
                # Check for key files indicating this is a valid installation
                if any([
                    os.path.exists(os.path.join(path, "horde-bridge.cmd")),
                    os.path.exists(os.path.join(path, "horde-bridge.sh")),
                    os.path.exists(os.path.join(path, "bridgeData_template.yaml")),
                    os.path.exists(os.path.join(path, "run_worker.py"))
                ]):
                    self.folder_path.setText(path)
                    self.append_log(f"Found worker installation at: {path}")
                    return True
        
        # If we get here, no installation was found
        QMessageBox.warning(
            self, 
            "Installation Not Found",
            "Could not locate the horde-worker-reGen installation automatically. Please browse to the folder."
        )
        return False
    
    def browse_worker_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select horde-worker-reGen Folder",
            self.folder_path.text() if self.folder_path.text() else os.path.expanduser("~")
        )
        
        if folder:
            self.folder_path.setText(folder)
            self.config_file = os.path.join(folder, "bridgeData.yaml")
            self.load_config()
    
    def load_default_config(self):
        if self.folder_path.text():
            self.config_file = os.path.join(self.folder_path.text(), "bridgeData.yaml")
            
            # Save the config file path to user settings so it's remembered across restarts
            settings_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings")
            os.makedirs(settings_dir, exist_ok=True)
            settings_file = os.path.join(settings_dir, "gui_settings.json")
            
            settings = {
                "worker_folder": self.folder_path.text(),
                "config_file": self.config_file
            }
            
            try:
                with open(settings_file, 'w') as f:
                    json.dump(settings, f)
            except Exception as e:
                print(f"Warning: Could not save settings: {e}")
                
            self.load_config()
    
    def load_config(self):
        if not self.config_file or not os.path.exists(self.config_file):
            # Check if template exists
            template_path = os.path.join(os.path.dirname(self.config_file), "bridgeData_template.yaml")
            if os.path.exists(template_path):
                QMessageBox.information(
                    self,
                    "Configuration Not Found",
                    "No configuration file found. A new one will be created based on the template."
                )
                # Copy template to config file
                with open(template_path, 'r') as f:
                    template_content = f.read()
                
                with open(self.config_file, 'w') as f:
                    f.write(template_content)
            else:
                QMessageBox.warning(
                    self,
                    "Template Not Found",
                    "Could not find the configuration template. Please ensure the worker is properly installed."
                )
                return
        
        try:
            with open(self.config_file, 'r') as f:
                self.config_data = yaml.safe_load(f)
            
            # Fill in form fields with loaded data
            self.populate_config_form()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading Configuration",
                f"Failed to load configuration: {str(e)}"
            )
    
    def populate_config_form(self):
        if not self.config_data:
            return
        
        # Basic settings
        if 'horde_api_key' in self.config_data:
            self.api_key_input.setText(self.config_data['horde_api_key'])
        
        if 'dreamer_name' in self.config_data:
            self.worker_name_input.setText(self.config_data['dreamer_name'])
        
        if 'nsfw' in self.config_data:
            self.nsfw_checkbox.setChecked(self.config_data['nsfw'])
        
        # Models to load
        if 'models_to_load' in self.config_data and self.config_data['models_to_load']:
            self.models_input.setText("\n".join(self.config_data['models_to_load']))
        
        # Performance settings
        if 'max_threads' in self.config_data:
            self.max_threads_spin.setValue(self.config_data['max_threads'])
        
        if 'max_power' in self.config_data:
            self.max_power_spin.setValue(self.config_data['max_power'])
        
        if 'queue_size' in self.config_data:
            self.queue_size_spin.setValue(self.config_data['queue_size'])
        
        if 'safety_on_gpu' in self.config_data:
            self.safety_on_gpu_checkbox.setChecked(self.config_data['safety_on_gpu'])
        
        if 'high_memory_mode' in self.config_data:
            self.high_memory_mode_checkbox.setChecked(self.config_data['high_memory_mode'])
        
        if 'max_batch' in self.config_data:
            self.max_batch_spin.setValue(self.config_data['max_batch'])
        
        # Feature settings
        if 'allow_lora' in self.config_data:
            self.allow_lora_checkbox.setChecked(self.config_data['allow_lora'])
        
        if 'allow_controlnet' in self.config_data:
            self.allow_controlnet_checkbox.setChecked(self.config_data['allow_controlnet'])
        
        if 'allow_sdxl_controlnet' in self.config_data:
            self.allow_sdxl_controlnet_checkbox.setChecked(self.config_data['allow_sdxl_controlnet'])
        
        if 'allow_post_processing' in self.config_data:
            self.allow_post_processing_checkbox.setChecked(self.config_data['allow_post_processing'])
        
        # Models to skip
        if 'models_to_skip' in self.config_data and self.config_data['models_to_skip']:
            self.models_skip_input.setText("\n".join(self.config_data['models_to_skip']))
    
    def save_config(self):
        if not self.config_file:
            QMessageBox.warning(
                self,
                "No Configuration File",
                "Please select the worker folder first."
            )
            return
        
        try:
            # Gather data from form fields
            self.config_data['horde_api_key'] = self.api_key_input.text()
            self.config_data['dreamer_name'] = self.worker_name_input.text()
            self.config_data['nsfw'] = self.nsfw_checkbox.isChecked()
            
            # Models to load (split by newlines and strip whitespace)
            models_text = self.models_input.toPlainText()
            if models_text:
                self.config_data['models_to_load'] = [m.strip() for m in models_text.split('\n') if m.strip()]
            else:
                self.config_data['models_to_load'] = []
            
            # Performance settings
            self.config_data['max_threads'] = self.max_threads_spin.value()
            self.config_data['max_power'] = self.max_power_spin.value()
            self.config_data['queue_size'] = self.queue_size_spin.value()
            self.config_data['safety_on_gpu'] = self.safety_on_gpu_checkbox.isChecked()
            self.config_data['high_memory_mode'] = self.high_memory_mode_checkbox.isChecked()
            self.config_data['max_batch'] = self.max_batch_spin.value()
            
            # Feature settings
            self.config_data['allow_lora'] = self.allow_lora_checkbox.isChecked()
            self.config_data['allow_controlnet'] = self.allow_controlnet_checkbox.isChecked()
            self.config_data['allow_sdxl_controlnet'] = self.allow_sdxl_controlnet_checkbox.isChecked()
            self.config_data['allow_post_processing'] = self.allow_post_processing_checkbox.isChecked()
            
            # Models to skip
            models_skip_text = self.models_skip_input.toPlainText()
            if models_skip_text:
                self.config_data['models_to_skip'] = [m.strip() for m in models_skip_text.split('\n') if m.strip()]
            else:
                self.config_data['models_to_skip'] = []
            
            # Save to file
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False)
            
            QMessageBox.information(
                self,
                "Configuration Saved",
                "The configuration has been saved successfully."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Saving Configuration",
                f"Failed to save configuration: {str(e)}"
            )
    
    def check_and_install_dependencies(self):
        """Check for required dependencies and install them if needed."""
        required_packages = [
            'loguru',        # Required for logging
            'pyyaml',        # Required for config management
            'requests',      # Required for API communication
            'tqdm',          # Required for progress bars
            'pillow',        # Required for image processing
            'numpy',         # Common dependency
            'torch',         # Required for AI models
            'transformers',  # Required for transformers models
            'diffusers',     # Required for diffusion models
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            result = QMessageBox.question(
                self,
                "Missing Dependencies",
                f"The following required packages are missing:\n{', '.join(missing_packages)}\n\nWould you like to install them now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if result == QMessageBox.StandardButton.Yes:
                # Create a progress dialog
                progress = QProgressDialog("Installing dependencies...", "Cancel", 0, len(missing_packages), self)
                progress.setWindowTitle("Installing Dependencies")
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.show()
                
                success = True
                for i, package in enumerate(missing_packages):
                    progress.setValue(i)
                    progress.setLabelText(f"Installing {package}...")
                    if progress.wasCanceled():
                        break
                    
                    # Install the package
                    try:
                        self.append_log(f"Installing {package}...")
                        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                        self.append_log(f"Successfully installed {package}")
                    except subprocess.CalledProcessError as e:
                        self.append_log(f"Failed to install {package}: {str(e)}")
                        success = False
                
                progress.setValue(len(missing_packages))
                
                if success:
                    QMessageBox.information(
                        self,
                        "Dependencies Installed",
                        "All dependencies have been successfully installed."
                    )
                    return True
                else:
                    QMessageBox.critical(
                        self,
                        "Installation Failed",
                        "Failed to install some dependencies. Please install them manually."
                    )
                    return False
            else:
                return False
        
        # All dependencies are already installed
        return True
    
    def toggle_worker(self):
        if self.worker_running:
            self.stop_worker()
        else:
            # Check dependencies before starting
            if self.check_and_install_dependencies():
                self.start_worker()
            else:
                self.append_log("Worker not started due to missing dependencies.")
    
    def install_specific_dependency(self, package_name):
        """Install a specific dependency directly"""
        try:
            self.append_log(f"Installing {package_name}...")
            # Use the system's Python to install the package
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.append_log(f"Successfully installed {package_name}")
                return True
            else:
                self.append_log(f"Failed to install {package_name}: {result.stderr}")
                return False
        except Exception as e:
            self.append_log(f"Error installing {package_name}: {str(e)}")
            return False
    
    def start_worker(self):
        if not self.folder_path.text():
            QMessageBox.warning(
                self,
                "Worker Folder Not Set",
                "Please select the worker folder first."
            )
            return
            
        # Directly install critical dependencies to make sure they're available
        critical_deps = ['loguru', 'pyyaml', 'requests']
        missing_critical = []
        
        for dep in critical_deps:
            try:
                importlib.import_module(dep)
            except ImportError:
                missing_critical.append(dep)
        
        if missing_critical:
            self.append_log(f"Installing critical dependencies: {', '.join(missing_critical)}")
            for dep in missing_critical:
                if not self.install_specific_dependency(dep):
                    QMessageBox.critical(
                        self,
                        "Critical Dependency Missing",
                        f"Could not install {dep}. The worker will not function without it."
                    )
                    return
        
        # Determine the appropriate worker script based on platform and GPU type
        if sys.platform == 'win32':
            # Check if DirectML version is needed (future enhancement)
            worker_script = os.path.join(self.folder_path.text(), "horde-bridge.cmd")
            
            # If not found, look for alternative versions
            if not os.path.exists(worker_script):
                # Try DirectML version
                worker_script = os.path.join(self.folder_path.text(), "horde-bridge-directml.cmd")
                
            # If still not found, try the Python script directly
            if not os.path.exists(worker_script):
                worker_script = os.path.join(self.folder_path.text(), "run_worker.py")
                
        else:  # Linux or macOS
            # Default script
            worker_script = os.path.join(self.folder_path.text(), "horde-bridge.sh")
            
            # Check for AMD version
            if not os.path.exists(worker_script):
                worker_script = os.path.join(self.folder_path.text(), "horde-bridge-rocm.sh")
                
            # If not found, try the Python script directly
            if not os.path.exists(worker_script):
                worker_script = os.path.join(self.folder_path.text(), "run_worker.py")
        
        # Final fallback to module directory
        if not os.path.exists(worker_script):
            worker_script = os.path.join(self.folder_path.text(), "horde_worker_regen", "run_worker.py")
            
        if not os.path.exists(worker_script):
                QMessageBox.warning(
                    self,
                    "Worker Script Not Found",
                    f"Could not find the worker script at {worker_script}"
                )
                return
        
        # Save configuration before starting
        self.save_config()
        
        # Clear the log display before starting
        self.log_display.clear()
        
        # Start worker in a separate thread
        self.worker_thread = WorkerThread(worker_script)
        self.worker_thread.update_status.connect(self.update_worker_status)
        self.worker_thread.update_status.connect(self.append_log)  # Direct connection to log display
        self.worker_thread.job_completed.connect(self.handle_job_completed)
        self.worker_thread.start()
        
        # Initialize log display
        self.append_log("Starting worker. Output will appear here...")
        
        # Update UI
        self.worker_running = True
        self.run_button.setText("Stop Worker")
        self.run_button.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold; padding: 8px 16px;")
        self.status_label.setText("Status: Running")
        self.status_label.setStyleSheet("font-weight: bold; color: #5cb85c;")
        
        # Record start time for uptime calculation
        self.start_time = time.time()
        
        # Start stats timer
        self.stats_timer.start(5000)
    
    def stop_worker(self):
        if self.worker_thread:
            self.worker_thread.stop()
            self.worker_thread = None
        
        if self.log_monitor:
            self.log_monitor.stop()
            self.log_monitor = None
        
        # Update UI
        self.worker_running = False
        self.run_button.setText("Start Worker")
        self.run_button.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold; padding: 8px 16px;")
        self.status_label.setText("Status: Not Running")
        self.status_label.setStyleSheet("font-weight: bold; color: #d9534f;")
        
        # Stop stats timer
        self.stats_timer.stop()
    
    def start_log_monitor(self):
        """
        Instead of monitoring log files, we'll capture output directly from the worker process
        and display it in the log text area. The output is already being captured in the
        WorkerThread and emitted through the update_status signal.
        """
        # Clear previous logs
        self.log_display.clear()
        
        # Add an initial message
        self.append_log("Starting log monitoring. Output from worker process will appear here...")
        
        # Update UI to show we're now displaying direct worker output
        self.log_file_combo.setEnabled(False)
        self.log_file_combo.setToolTip("Log monitoring is now done directly from worker output")
        
        # Add a timestamp to the log
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.append_log(f"[{timestamp}] Worker process started")
    
    def change_log_file(self, log_file):
        """
        Handle changing between different log sources.
        - "Direct Output" shows output directly from the worker process
        - Other options read from the respective log files
        """
        # Clear the display
        self.log_display.clear()
        
        # Handle direct output mode
        if log_file == "Direct Output":
            if self.worker_running:
                self.append_log("Switched to direct worker output mode.")
                self.append_log("Displaying real-time output from the worker process.")
            else:
                self.append_log("Direct output mode selected.")
                self.append_log("Start the worker to see output.")
            return
        
        # For file-based logs
        if not self.folder_path.text():
            self.append_log("Worker folder not set. Cannot read log files.")
            return
            
        # Determine log file location
        log_dir = os.path.join(self.folder_path.text(), "logs")
        log_path = os.path.join(log_dir, log_file)
        
        if not os.path.exists(log_path):
            self.append_log(f"Log file not found: {log_path}")
            self.append_log("The log file may not have been created yet.")
            return
            
        # Read the log file and display its contents
        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                # For large log files, only read the last 500 lines to avoid performance issues
                lines = f.readlines()
                if len(lines) > 500:
                    self.append_log(f"Log file is large. Showing last 500 of {len(lines)} lines.")
                    lines = lines[-500:]
                
                for line in lines:
                    self.log_display.append(line.rstrip())
                    
            self.append_log(f"Loaded log file: {log_path}")
            
            # If worker is running and we're showing a file, add a note
            if self.worker_running:
                self.append_log("NOTE: This log file view is static. Switch to 'Direct Output' for real-time updates.")
                
        except Exception as e:
            self.append_log(f"Error reading log file: {str(e)}")
    
    def append_log(self, line):
        """
        Append a line to the log display and auto-scroll to the bottom.
        This can be called at any time, even before the worker starts.
        """
        # Format the line with a timestamp if it doesn't already have one
        if not line.startswith('[20') and not line.startswith('---'):  # Skip if already has timestamp
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{timestamp}] {line}"
            
        self.log_display.append(line)
        
        # Auto-scroll to bottom
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_display.setTextCursor(cursor)
    
    def update_worker_status(self, status):
        if "Job completed" in status:
            self.jobs_completed += 1
            self.jobs_label.setText(f"Jobs Completed: {self.jobs_completed}")
            
            # Extract kudos info if available
            if "Kudos earned" in status:
                try:
                    kudos_text = status.split("Kudos earned:")[1].strip()
                    kudos = float(kudos_text.split()[0])
                    self.kudos_earned += kudos
                    self.kudos_label.setText(f"Kudos Earned: {self.kudos_earned:.2f}")
                except:
                    pass
        
        # Update current job info
        if "Processing job" in status:
            self.current_job_label.setText(status)
        
        # Add to jobs text display
        if any(x in status for x in ["Job completed", "Processing job", "Kudos earned"]):
            timestamp = time.strftime("%H:%M:%S")
            self.jobs_text.append(f"[{timestamp}] {status}")
    
    def handle_job_completed(self, job_info):
        # This method can be expanded to handle more detailed job information
        self.jobs_completed += 1
        self.jobs_label.setText(f"Jobs Completed: {self.jobs_completed}")
    
    def update_stats(self):
        if not self.worker_running:
            return
        
        # Update uptime
        uptime_secs = int(time.time() - self.start_time)
        hours = uptime_secs // 3600
        minutes = (uptime_secs % 3600) // 60
        seconds = uptime_secs % 60
        self.uptime_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")
        
        # Calculate kudos rate (kudos per hour)
        if uptime_secs > 0:
            kudos_per_hour = (self.kudos_earned / uptime_secs) * 3600
            self.kudos_rate_label.setText(f"{kudos_per_hour:.2f} / hour")
    
    def update_worker(self):
        if not self.folder_path.text():
            QMessageBox.warning(
                self,
                "Worker Folder Not Set",
                "Please select the worker folder first."
            )
            return
        
        try:
            if sys.platform == 'win32':
                # On Windows, run a git pull or download new zip
                if os.path.exists(os.path.join(self.folder_path.text(), ".git")):
                    # Use git pull
                    subprocess.run(
                        ["git", "pull"],
                        cwd=self.folder_path.text(),
                        check=True
                    )
                    QMessageBox.information(
                        self,
                        "Update Successful",
                        "The worker has been updated successfully using git pull."
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Manual Update Required",
                        "This installation doesn't use git. Please download the latest version from GitHub."
                    )
                    QDesktopServices.openUrl(QUrl("https://github.com/Haidra-Org/horde-worker-reGen/archive/main.zip"))
            else:
                # On Linux/Mac, run git pull
                if os.path.exists(os.path.join(self.folder_path.text(), ".git")):
                    subprocess.run(
                        ["git", "pull"],
                        cwd=self.folder_path.text(),
                        check=True
                    )
                    QMessageBox.information(
                        self,
                        "Update Successful",
                        "The worker has been updated successfully using git pull."
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Manual Update Required",
                        "This installation doesn't use git. Please download the latest version from GitHub."
                    )
                    QDesktopServices.openUrl(QUrl("https://github.com/Haidra-Org/horde-worker-reGen/archive/main.zip"))
        except Exception as e:
            QMessageBox.critical(
                self,
                "Update Failed",
                f"Failed to update the worker: {str(e)}"
            )
    
    def open_logs_folder(self):
        """Open the logs folder in the system file explorer"""
        if not self.folder_path.text():
            QMessageBox.warning(
                self,
                "Worker Folder Not Set",
                "Please select the worker folder first."
            )
            return
        
        # Determine logs folder location
        logs_dir = os.path.join(self.folder_path.text(), "logs")
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(logs_dir):
            try:
                os.makedirs(logs_dir)
                self.append_log(f"Created logs directory: {logs_dir}")
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Error Creating Logs Folder",
                    f"Could not create logs folder: {str(e)}"
                )
                return
        
        # Open the logs folder using the system file explorer
        try:
            if sys.platform == 'win32':
                os.startfile(logs_dir)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', logs_dir])
            else:  # Linux
                subprocess.run(['xdg-open', logs_dir])
            
            self.append_log(f"Opened logs folder: {logs_dir}")
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error Opening Logs Folder",
                f"Could not open logs folder: {str(e)}"
            )
            
    def update_runtime(self):
        if not self.folder_path.text():
            QMessageBox.warning(
                self,
                "Worker Folder Not Set",
                "Please select the worker folder first."
            )
            return
        
        try:
            if sys.platform == 'win32':
                # On Windows, run update-runtime.cmd
                update_script = os.path.join(self.folder_path.text(), "update-runtime.cmd")
                if os.path.exists(update_script):
                    subprocess.run(
                        [update_script],
                        cwd=self.folder_path.text(),
                        check=True
                    )
                    QMessageBox.information(
                        self,
                        "Runtime Updated",
                        "The runtime has been updated successfully."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Update Script Not Found",
                        f"Could not find the update script at {update_script}"
                    )
            else:
                # On Linux/Mac, run update-runtime.sh
                update_script = os.path.join(self.folder_path.text(), "update-runtime.sh")
                if os.path.exists(update_script):
                    subprocess.run(
                        ["bash", update_script],
                        cwd=self.folder_path.text(),
                        check=True
                    )
                    QMessageBox.information(
                        self,
                        "Runtime Updated",
                        "The runtime has been updated successfully."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Update Script Not Found",
                        f"Could not find the update script at {update_script}"
                    )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Runtime Update Failed",
                f"Failed to update the runtime: {str(e)}"
            )
    
    def open_logs_folder(self):
        if not self.folder_path.text():
            QMessageBox.warning(
                self,
                "Worker Folder Not Set",
                "Please select the worker folder first."
            )
            return
        
        logs_dir = os.path.join(self.folder_path.text(), "logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Open folder in file explorer
        if sys.platform == 'win32':
            os.startfile(logs_dir)
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', logs_dir])
        else:  # Linux
            subprocess.run(['xdg-open', logs_dir])
    
    def refresh_model_list(self):
        if not self.folder_path.text():
            QMessageBox.warning(
                self,
                "Worker Folder Not Set",
                "Please select the worker folder first."
            )
            return
        
        # Clear current list
        self.model_tree.clear()
        
        # Check for models.json
        models_file = os.path.join(self.folder_path.text(), "models.json")
        if not os.path.exists(models_file):
            QMessageBox.information(
                self,
                "Models File Not Found",
                "Could not find models.json file. It may be generated when you first run the worker."
            )
            return
        
        try:
            with open(models_file, 'r') as f:
                models_data = json.load(f)
            
            # Group models by type
            model_types = {}
            for model in models_data:
                model_type = model.get('type', 'Unknown')
                if model_type not in model_types:
                    model_types[model_type] = []
                model_types[model_type].append(model)
            
            # Add to tree
            for model_type, models in model_types.items():
                type_item = QTreeWidgetItem(self.model_tree, [model_type])
                
                for model in models:
                    model_name = model.get('name', 'Unknown')
                    model_status = "Available"
                    model_size = f"{model.get('filesize', 0) / (1024*1024):.1f} MB"
                    
                    QTreeWidgetItem(type_item, [model_name, "", model_status, model_size])
            
            # Expand all items
            self.model_tree.expandAll()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading Models",
                f"Failed to load models: {str(e)}"
            )
    
    def add_custom_model(self):
        if not self.folder_path.text():
            QMessageBox.warning(
                self,
                "Worker Folder Not Set",
                "Please select the worker folder first."
            )
            return
        
        # A more comprehensive custom model dialog could be implemented here
        QMessageBox.information(
            self,
            "Custom Models",
            "To add custom models, edit the 'custom_models' section in your bridgeData.yaml file.\n\n"
            "The format is:\n\n"
            "custom_models:\n"
            "  - name: My Custom Model\n"
            "    baseline: stable_diffusion_xl\n"
            "    filepath: /path/to/model/file.safetensors"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show the main window
    window = HordeWorkerGUI()
    window.show()
    
    sys.exit(app.exec())
