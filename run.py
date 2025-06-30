#!/usr/bin/env python3
import sys
import subprocess
import importlib

def check_and_install_dependencies():
    """
    Check for required dependencies and install them if missing.
    """
    # Dictionary mapping import names to their pip package names
    # Some packages have different import names than pip package names
    dependencies = {
        'PyQt6': 'PyQt6',
        'yaml': 'pyyaml',          # Import name is 'yaml', pip package is 'pyyaml'
        'loguru': 'loguru',
        'torchaudio': 'torchaudio',
        'matplotlib': 'matplotlib',
        'tqdm': 'tqdm',
        'requests': 'requests',
        'git': 'gitpython'         # Import name is 'git', pip package is 'gitpython'
    }
    
    missing_modules = []
    
    # First, just check dependencies without any user interaction
    for import_name, package_name in dependencies.items():
        try:
            importlib.import_module(import_name)
            print(f"✓ {import_name} ({package_name}) is installed")
        except ImportError:
            missing_modules.append((import_name, package_name))
            print(f"✗ {import_name} ({package_name}) is missing")
    
    # If missing dependencies, handle installation
    if missing_modules:
        packages_to_install = [pkg_name for _, pkg_name in missing_modules]
        print(f"\nMissing dependencies: {', '.join(packages_to_install)}")
        
        # Since this is a GUI app, let's use a non-interactive approach
        # We'll install dependencies automatically without prompting
        print("Installing missing dependencies automatically...")
        
        install_errors = []
        for _, package_name in missing_modules:
            try:
                print(f"\nInstalling {package_name}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
                print(f"Successfully installed {package_name}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {package_name}: {e}")
                install_errors.append(package_name)
        
        if install_errors:
            print(f"\nWarning: Failed to install: {', '.join(install_errors)}")
            print("The application may not function correctly.")
            print("You may need to manually install these packages:")
            for package in install_errors:
                print(f"  pip install {package}")
        else:
            print("\nAll dependencies installed successfully!")
    else:
        print("All dependencies are installed!")
    
    print("Starting application...\n")

def main():
    """
    Main entry point for the AI Horde Worker reGen GUI application.
    """
    # Check and install dependencies
    check_and_install_dependencies()
    
    # Now import Qt and GUI after ensuring dependencies are installed
    from PyQt6.QtWidgets import QApplication
    from horde_worker_gui import HordeWorkerGUI
    
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show the main window
    window = HordeWorkerGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
