# RUGA CLI Quick Start

## Installation

1. **Install dependencies:**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -e .
   ```

2. **Verify installation:**
   ```bash
   # Run as module
   python -m ruga_cli --help
   
   # Or if installed with entry point
   ruga --help
   ```

## Start the Server

Before using the CLI, make sure the RUGA server is running:

```bash
# From the project root
cd backend
python main.py

# Or using uvicorn directly
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Basic Usage

### 1. Check Server Connection

```bash
ruga info
# or
python -m ruga_cli info
```

### 2. List Files

```bash
ruga files list ./examples/unstructured_folder
```

### 3. Analyze Files

```bash
# Analyze entire folder
ruga analyze folder ./examples/unstructured_folder

# Analyze single file
ruga analyze file ./examples/unstructured_folder/some_pdfs/presentation_final_v2_FINAL.pdf
```

### 4. Check Job Status

```bash
# List all jobs
ruga jobs list

# Get specific job details
ruga jobs get <job_id>
```

### 5. Organize Folder

```bash
# Generate structure
ruga organize generate ./examples/unstructured_folder

# Apply structure (use structure_id from previous command)
ruga organize apply <structure_id>

# Or do everything at once
ruga organize all ./examples/unstructured_folder
```

### 6. Chat with Documents

```bash
ruga chat "What documents discuss survival analysis?"
ruga chat "Find documents about causal inference"
```

## Configuration

Set server URL via environment variable:

```bash
export RUGA_SERVER_URL="http://localhost:8000"
ruga info
```

Or use command-line option:

```bash
ruga --server-url http://localhost:8000 info
```

## Troubleshooting

**"Connection refused" or "Cannot connect":**
- Make sure the server is running: `cd backend && python main.py`
- Check the server URL: `ruga info --server-url http://localhost:8000`

**"Command not found: ruga":**
- Install in editable mode: `pip install -e .` or `uv sync`
- Or use: `python -m ruga_cli` instead of `ruga`

**Import errors:**
- Make sure all dependencies are installed: `uv sync`
- Check Python version: `python --version` (requires >= 3.11)
