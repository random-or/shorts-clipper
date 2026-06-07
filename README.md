---
title: Shorts Clipper
emoji: 🎬
colorFrom: red
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

<div align="center">

# 🎬 Shorts Clipper

### **The Enterprise-Grade AI Shorts Factory**

*Scout trending videos → Extract viral highlights → Render vertical crops → Burn animated captions → Auto-publish to YouTube.*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Docker Ready](https://img.shields.io/badge/docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](#-docker--cloud-deployment)

![Web UI Dashboard](./docs/images/dashboard_preview.png)
</div>

---

## 🔥 What is this?
**Shorts Clipper** completely automates the process of turning long, boring YouTube videos (like podcasts, streams, or lectures) into highly engaging, vertical 9:16 Shorts. Just give it a YouTube link or a topic, and the built-in AI will find the best clips, crop the faces, burn dynamic subtitles, and can even upload them directly to your channel.

---

## ⚡ The "I'm Lazy" 1-Minute Setup

We know you want to get straight to clipping. Here is the absolute fastest way to get started.

### 📋 Requirements
- **Python 3.11+**
- **FFmpeg** installed on your system
- A free **Google Gemini API Key** from [Google AI Studio](https://aistudio.google.com/)

### 🚀 Install & Run
Run these commands in your terminal:

```bash
git clone https://github.com/random-or/shorts-clipper.git
cd shorts-clipper

# Create environment & install
python -m venv env
source env/bin/activate  # (On Windows use: env\Scripts\activate)
pip install -e .

# Add your Gemini Key
echo "GEMINI_API_KEY=your_key_here" > .env
```

### 🖥️ Start the Web UI
```bash
python -m shorts_clipper web
```
👉 Open **http://127.0.0.1:8000** in your browser and you're ready to clip!

---

## 🚀 Key Features (Why it's Goated)

*   **🧠 Fully Autonomous Pipeline:** Drop a link, let the Gemini AI find the most viral moments, crop them, and subtitle them. Zero manual editing required.
*   **🛡️ Anti-Ban Download System:** Built-in Chrome browser impersonation ensures your downloads are never blocked or rate-limited by YouTube.
*   **🎨 Custom Caption Studio:** Choose from popular TikTok/Reels subtitle styles (like *Hormozi Glow* or *MrBeast Pop*) or create your own.
*   **⚙️ Background Rendering Engine:** The built-in SQLite job queue processes long renders and uploads in the background. Your Web UI will never freeze.

---

## 🐳 Docker (For the truly lazy)

Don't want to install Python or FFmpeg? Use Docker:

```bash
# 1. Add your API key to .env
echo "GEMINI_API_KEY=your_key_here" > .env

# 2. Build and run
docker build -t shorts-clipper .
docker run -p 8000:7860 --env-file .env shorts-clipper
```
Open **http://127.0.0.1:8000** and start clipping.

---

## 🧠 Advanced CLI Usage

Prefer the terminal? We got you.

```bash
# Clip a specific video
python -m shorts_clipper clip "https://youtube.com/watch?v=VIDEO_ID" --count 1

# Auto-Scout a niche and clip trending videos automatically
python -m shorts_clipper autopilot --niche "motivation" --count 2

# Just scout for trending video links
python -m shorts_clipper scout --niche "gaming" --count 5
```

---

## 🔑 Auto-Publish to YouTube

Want it to automatically upload the finished Shorts? 
1. Enable the **YouTube Data API v3** in Google Cloud Console.
2. Download your OAuth Desktop credentials as `client_secret.json` and put it in the project folder.
3. Open the Web UI, click the user profile icon, and link your channel in 1 click.

---

## 📄 License
This project is open-source and licensed under the MIT License.
