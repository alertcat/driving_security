# DriveVision AI

Welcome to **DriveVision AI**, an innovative driving technology designed to enhance safety, convenience, and visibility for drivers through advanced AI and augmented reality (AR) features. This project integrates a suite of cutting-edge tools, including an LLM-powered chatbot, AR windscreen displays, and AI-driven vision enhancement systems.

<img width="703" alt="image" src="https://github.com/user-attachments/assets/d5e1240d-8c74-4742-abf2-1f8f10a1c9a1" />

## Overview
DriveVision AI redefines the driving experience by combining artificial intelligence with automotive technology. Key features include:

- **LLM Chatbot Assistance**: A language model-powered chatbot that assists drivers by referencing car manuals to troubleshoot issues and provide repair guidance. In the future, it will also adjust car settings dynamically based on user preferences or conditions.

- **AR Windscreen HUD**: An augmented reality windscreen that displays heads-up display (HUD) elements such as road navigation, real-time restaurant reviews based on the driver’s line of sight, and critical driving information.

- **AI-Powered Vision Enhancement**: An intelligent rain and fog removal system that enhances road visibility by processing and clarifying the view displayed on the windscreen.

- **Trajectory Detection & Warnings**: Real-time detection of pedestrians and vehicles, with AR overlays (e.g., circling objects on the windscreen) to alert drivers of potential hazards.


This project aims to make driving safer, more intuitive, and enjoyable by leveraging AI and AR technologies.

## Getting Started

### Prerequisites
- Python 3.x installed on your system.
- Git installed to clone the repository.
- Required hardware: A compatible AR windscreen setup and sensors (specific hardware details TBD).
- Optional: A virtual environment tool like `venv` for dependency management.

### Installation

#### Clone the Repository:
```bash
git clone https://github.com/alertcat/driving_security.git
cd driving_security
```

#### Set Up a Virtual Environment (Recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Install Dependencies:
```bash
pip install -r requirements.txt
```

#### Run the Application:
```bash
python ./backend/run.py
python ./frontend/Eye_Tracking/eye_tracking_OCR.py
cd ./frontend/des_frontend
flutter run
```

## Usage

Once installed, launch the DriveVision AI system by running `main.py`. The application will initialize the following features:

- **Chatbot**: Interact with the LLM chatbot via text or voice commands to get repair advice or car setting recommendations. Example:
  ```text
  "How do I fix a flat tire on a 2023 Tesla Model Y?"
  ```
- **AR HUD**: Connect the system to your AR windscreen hardware to display navigation, restaurant reviews, and driving alerts.
- **Vision Enhancement**: Activate the rain/fog removal feature to improve visibility in adverse weather conditions.
- **Safety Alerts**: The AI will automatically detect and highlight pedestrians or vehicles in your path on the windscreen.

For detailed commands or hardware setup instructions, refer to inline documentation in `main.py` or additional guides (to be developed).

## Contact
For questions, feedback, or support, please feel free to email us:
1. Long Zhen: e1351306@u.nus.edu
2. Zhou Yukang: e1350979@u.nus.edu
3. Choy Min Han: choymh23@u.nus.edu
