# AIDO - Local AI Assistant

AIDO is a local AI assistant powered by Qwen2.5, designed with precision, intelligence, and subtle personality inspired by HEUSC and JARVIS.

## Features

- Natural language command processing
- Persistent memory using mem0
- Modular configuration for easy extension
- Local execution for privacy

## Requirements

- Python 3.8+
- At least 8GB RAM (16GB+ recommended)
- GPU recommended for better performance

## Installation

1. Clone or download the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the assistant:
```bash
"C:/Users/duart/AppData/Local/Programs/Python/Python311/python.exe" aido.py
```

Or add Python to your PATH to use `python aido.py`.

**Note**: The first run will download the Qwen2.5-3B model (~6GB), which may take several minutes depending on your internet connection. Subsequent runs will be faster.

Interact by starting commands with "AIDO,":
- "AIDO, analyze this text"
- "AIDO, check system status"
- "AIDO, exit" to quit

## Configuration

The assistant behavior is defined in `aido_system_prompt.txt`. Modify this file to customize personality and capabilities.

## Troubleshooting

- **Model loading fails**: The 3B model requires ~8GB RAM. If still failing, try the 1.5B model by changing `model_name` in `aido.py` to `"Qwen/Qwen2.5-1.5B-Instruct"`
- **Memory issues**: Check mem0 configuration and disk space.
- **Import errors**: Verify all packages are installed correctly.

## Memory System

AIDO uses mem0 with a local Chroma vector store for persistent memory. No API key is required for local operation. Memory data is stored in the `./chroma_db` directory.

If you prefer cloud-based memory (e.g., using OpenAI embeddings), set the appropriate environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- Or other provider keys as supported by mem0

Modify the `config` dictionary in `aido.py` to change memory providers.

## License

[Add license if applicable]