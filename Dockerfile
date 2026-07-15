# Start from Ubuntu 20.04
FROM ubuntu:20.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Python, pip, and actual system-level GUI libraries
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    # --- GUI & Qt Dependencies needed for bundling ---
    libglib2.0-0 \
    libfontconfig1 \
    libdbus-1-3 \
    libxkbcommon0 \
    libx11-6 \
    libfreetype6 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and install PyInstaller + PyQt6
RUN pip3 install --upgrade pip setuptools
RUN pip3 install pyinstaller PyQt6

# Set the working directory inside the container
WORKDIR /build
