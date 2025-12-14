# Ruga Backend API

FastAPI server for managing file analysis and .ruga metadata generation.

## Features

- List all files and folders recursively from a root path
- Check which files have associated .ruga metadata files
- View .ruga file content for analyzed files
- Start background analysis jobs to generate .ruga files
- Poll analysis status for individual files

## Installation

Install dependencies from the project root:

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Environment Setup

The server requires an OpenAI API key for file analysis. Create a `.env` file in the project root with your API key:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your OpenAI API key
OPENAI_API_KEY="your-openai-api-key-here"
```

See `.env.example` for the required environment variables.

## Running the Server

From the project root:

```bash
# Using uvicorn directly
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python
python -m backend.main
```

The server will be available at `http://localhost:8000`

## API Endpoints

### GET `/`

Root endpoint with API information.

### GET `/files?root_path=<path>`

List all files and folders recursively from a root path.

**Query Parameters:**
- `root_path` (required): Path to the root directory to scan

**Response:**
```json
{
  "root_path": "/absolute/path/to/root",
  "files": [
    {
      "path": "relative/path/to/file.txt",
      "is_directory": false,
      "has_ruga": true,
      "ruga_content": { ... },
      "size": 1234
    },
    ...
  ]
}
```

### POST `/analyze/folder`

Start analyzing all files in a folder and generating .ruga files as background tasks.

**Request Body:**
```json
{
  "root_path": "/path/to/root"
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Queued 5 file(s) for analysis",
  "job_type": "folder",
  "root_path": "/absolute/path/to/root",
  "target_path": "/absolute/path/to/root",
  "files_queued": 5,
  "file_paths": ["file1.txt", "file2.pdf", ...]
}
```

### POST `/analyze/file`

Start analyzing a single file and generating a .ruga file as a background task.

**Request Body:**
```json
{
  "absolute_path": "/absolute/path/to/file.txt",
  "root_path": "/path/to/root"  // Optional: if not provided, uses parent directory of file
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Queued file for analysis",
  "job_type": "file",
  "root_path": "/absolute/path/to/root",
  "target_path": "relative/path/to/file.txt",
  "files_queued": 1,
  "file_paths": ["relative/path/to/file.txt"]
}
```

**Note:** If `root_path` is not provided, the parent directory of the file will be used as the root, and the relative path will be just the filename.

### GET `/jobs`

List all analysis jobs with their status.

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "job_type": "folder",
      "root_path": "/absolute/path/to/root",
      "target_path": "/absolute/path/to/root",
      "status": "in_process",
      "files_queued": 5,
      "files_processed": 2,
      "files_failed": 0,
      "created_at": "2024-01-01T12:00:00",
      "error_message": null
    },
    {
      "job_id": "660e8400-e29b-41d4-a716-446655440001",
      "job_type": "file",
      "root_path": "/absolute/path/to/root",
      "target_path": "file.txt",
      "status": "analyzed",
      "files_queued": 1,
      "files_processed": 1,
      "files_failed": 0,
      "created_at": "2024-01-01T11:00:00",
      "error_message": null
    }
  ]
}
```

### GET `/status/{file_path}?root_path=<path>`

Get the analysis status for a specific file.

**Path Parameters:**
- `file_path`: Relative path to the file (from root_path)

**Query Parameters:**
- `root_path` (required): Root directory path

**Response:**
```json
{
  "file_path": "relative/path/to/file.txt",
  "root_path": "/absolute/path/to/root",
  "status": "analyzed",  // One of: "analyzed", "in_process", "error", "not_found", "pending"
  "error_message": null  // Only present if status is "error"
}
```

**Status Values:**
- `analyzed`: File has been analyzed and .ruga file exists
- `in_process`: File is currently being analyzed
- `error`: Analysis failed (check error_message)
- `not_found`: File not found or not queued for analysis
- `pending`: File is queued but not yet started

**Job Types:**
- `folder`: Job for analyzing all files in a folder
- `file`: Job for analyzing a single file

## Example Usage

### List files in a directory

```bash
curl "http://localhost:8000/files?root_path=/path/to/examples/unstructured_folder"
```

### Start analyzing a folder

```bash
curl -X POST "http://localhost:8000/analyze/folder" \
  -H "Content-Type: application/json" \
  -d '{"root_path": "/path/to/examples/unstructured_folder"}'
```

### Start analyzing a single file

```bash
curl -X POST "http://localhost:8000/analyze/file" \
  -H "Content-Type: application/json" \
  -d '{
    "absolute_path": "/absolute/path/to/examples/unstructured_folder/file1.txt"
  }'
```

Or with explicit root path:

```bash
curl -X POST "http://localhost:8000/analyze/file" \
  -H "Content-Type: application/json" \
  -d '{
    "absolute_path": "/absolute/path/to/examples/unstructured_folder/file1.txt",
    "root_path": "/absolute/path/to/examples/unstructured_folder"
  }'
```

### List all jobs

```bash
curl "http://localhost:8000/jobs"
```

### Check analysis status

```bash
curl "http://localhost:8000/status/file1.txt?root_path=/path/to/examples/unstructured_folder"
```

## API Documentation

When the server is running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

The backend uses:
- FastAPI for the web framework
- Pydantic for data validation
- Background tasks for async file processing
- Thread pool executor for CPU-intensive analysis tasks

**Important:** Make sure you have a `.env` file with `OPENAI_API_KEY` set (see `.env.example` for reference). The analysis functionality requires this API key to process files.

## Notes

- File paths in requests should use forward slashes (`/`) even on Windows
- The `root_path` should be an absolute path or a path relative to the server's working directory
- Analysis jobs run in the background and can be polled using the status endpoint
- The server maintains in-memory status tracking (status is lost on server restart)
