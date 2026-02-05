# Auto Media Validator 🚀

**Auto Media Validator** is a high-performance, open-source tool designed for the mass recursive integrity verification of media files. By leveraging the **FFmpeg** engine and **NVIDIA CUDA Hardware Acceleration**, it detects stream corruptions, bit errors, and damaged headers at exceptional speeds.

This tool was created to provide a professional solution for validating large media libraries, especially those recovered from failing storage systems or network shares.

---

## Key Features

* **🔍 Recursive Deep Scan**: Automatically explores subdirectories and network shares (NAS/SMB).
* **⚡ CUDA Hardware Acceleration**: Optimized for NVIDIA GPUs to process files at 40x-80x real-time speed.
* **📊 Live Performance Monitoring**:
    * **CPU Usage**: Real-time tracking of processor load.
    * **GPU Load & DEC**: Dedicated tracking for GPU processing and Video Decoder (NVDEC) engines.
    * **Processing Speed**: Live x-ratio speed metrics.
* **⏯️ Full Process Control**: Pause, Resume, and Stop functionality with safe process termination.
* **🌓 Adaptive UI**: Includes Dark/Light modes and bilingual support (English/Spanish).
* **🔕 Silent Operation**: Runs as a windowed application (`.pyw`), suppressing intrusive command prompts.

---

## 🛠 Prerequisites

### Dependencies
Install the required Python libraries:
```bash
pip install psutil nvidia-ml-py static-ffmpeg
```
## Installation & Usage
Setup: Save the script with a .pyw extension to ensure a console-free execution.

Select Path: Choose the root folder or network drive containing the files you wish to validate.

Configure Hardware: Toggle the CUDA Acceleration checkbox to offload decoding to your NVIDIA GPU.

Run: Monitor the log area for real-time status. Valid files receive a ✅ while corrupt files are flagged with a ❌.
