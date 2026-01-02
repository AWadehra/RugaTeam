# RUGA Web Frontend

This project was started as part of AI for Good hackathon and attempts to reduce overhead workflow of medical researchers so they can spend their time doing what they do best.

A modern web interface for RUGA, built with SvelteKit 2 and Svelte 5.

## Features

- **List Files**: View all files in a directory with `.ruga` analysis status
- **Analyze All**: Analyze files with real-time progress tracking (shows per-file status)
- **Organize**: Two-step flow - preview suggested structure, then apply
- **Chat**: RAG-powered chat with streaming responses
- **Smart UI**: Buttons auto-disable when actions aren't applicable

## Developing

### Setting up the Environment

Copy the `.example.env` file into a `.env` file

```env
VITE_API_BASE_URL=http://localhost:5173/api
API_RUGA_SERVER=http://localhost:8000
```

### Prerequisites

- Node.js 18+
- RUGA backend running on `http://localhost:8000`

### Running the application

You can start the application in either of the ways below

#### Docker-based run with podman
1. `podman build -t ruga-web .`
2. `podman run -p 5173:5173 ruga-web`

#### Running things locally with npm
1. `npm install`
2. `npm run dev -- --open`

### Using the application

1. **Enter a folder path** in the input field (e.g., `D:\Documents\Research`)
2. **Click "List Files"** to see all files and their analysis status
3. **Click "Analyze All (N)"** to analyze files without `.ruga` metadata
   - Watch real-time progress with per-file status updates
4. **Click "Organize (N)"** to organize analyzed files
   - Preview the suggested folder structure
   - Review file moves with reasons
   - Click "Apply" to create the organized folder
5. **Use the Chat** panel to ask questions about your documents
   - You can drag and drop files from the file list into the chat window context

## Tech Stack

- **SvelteKit 2** - Web framework with SSR
- **Svelte 5** - UI with Runes reactivity
- **TailwindCSS 4** - Utility-first styling
- **TanStack Table** - Headless table for file listing
- **Lucide Icons** - Icon library

## Development Commands

```bash
# Run dev server
npm run dev

# Type check
npm run check

# Build for production
npm run build

# Preview production build
npm run preview
```
