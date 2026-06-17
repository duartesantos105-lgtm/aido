# AIDO - Advanced Intelligence & Digital Operations

AIDO is an AI desktop assistant with a cyberpunk UI, powered by **Groq API (Llama 3.3-70B)**. Inspired by HEUSC (The Millionaire Detective) and JARVIS (Marvel).

## Features

- **AI Chat** with streaming responses via Groq API
- **Persistent Memory** using mem0 + ChromaDB
- **Voice Input** (Portuguese PT/BR)
- **Facial Recognition** login via DeepFace + OpenCV
- **PC Actions** — open browsers, file explorer, run scripts
- **Role-Based Access Control** — Guest / User / Sub-Admin / Admin
- **Self-Evolution** — AIDO can update its own system prompt
- **Code Self-Modification** — AIDO can propose rewriting its own source code
- **Wake Word** — requires "AIDO" after inactivity timeout
- **Cyberpunk UI** — neural network animation, glow effects, dark theme

## Requirements

- Python 3.10+
- Groq API key (free at https://console.groq.com)
- mem0 API key (free at https://mem0.ai)
- Windows (for PC actions; others limited)

## Installation

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your API keys:
```
GROQ_API_KEY=gsk_your_key_here
MEM0_API_KEY=m0_your_key_here
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_google_search_engine_id_here
```

## Usage

Run from the repo root:

```bash
python aido.py
```

Or directly:

```bash
python AIDO/ui.py
```

Login with default credentials: `duarte` / `admin`

Interact by saying "AIDO" followed by your command:
- "AIDO, open browser"
- "AIDO, what is the weather?"
- "AIDO, read my files"

## Admin CLI

Manage users and permissions:

```bash
python AIDO/admin_cli.py
```

## Project Structure

```
├── aido.py                  # Entry point
├── AIDO/
│   ├── ui.py                # Main GUI (customtkinter)
│   ├── brain.py             # AI brain (Groq API)
│   ├── auth.py              # Authentication & RBAC
│   ├── tools.py             # Web search, file tools
│   ├── pc_actions.py        # PC automation
│   ├── aido_overlay.py      # Fullscreen overlay animation
│   ├── roles.py             # RBAC system
│   ├── admin_cli.py         # Admin command-line tool
│   ├── aido_system_prompt.txt  # AI personality config
│   ├── requirements.txt     # Python dependencies
│   └── roles_config.json    # Role definitions
```

## Security

- `.env` is gitignored — never commit API keys
- `auth.json` is gitignored — created on first run with machine-bound credentials
- Password changes only allowed on the original machine
- PC actions require re-authentication
