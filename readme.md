# AI Horde Worker reGen GUI

A PyQt6 graphical interface for managing and monitoring your AI Horde Worker reGen contribution.

## Features

- Easy configuration of worker settings
- Real-time monitoring of worker status
- Log viewing and management
- Statistics tracking
- Model management

## Installation

1. Ensure you have Python 3.9+ installed
2. Clone this repository
3. Run `pip install -r requirements.txt` to install dependencies
4. Run `python run.py` to start the application

## Dependencies

- PyQt6
- pyyaml
- loguru
- gitpython (optional, for update features)
- torchaudio (for worker functionality)
- matplotlib (for worker functionality)
- tqdm (for worker functionality)
- requests (for API communication)

## Settings

The application stores its settings in the `settings` directory, which is created automatically when you first run the application. This includes:

- Previously used worker folder
- Configuration file location
- UI preferences

## License

This project is licensed under the MIT License - see the LICENSE file for details.
