# sv

This project was started as part of AI for Good hackathon and attempts to reduce overhead workflow of medical researchers so they can spend their time doing what they do best

## Developing

### Setting up the Environment

Copy the `.example.env` file into a `.env` file

### Running the application

You can start the application in either of the ways below

#### Docker-based run with podman
1. `podman build -t ruga-web .`
2. `podman run -p 5173:5173 ruga-web`

#### Running things locally with npm
1. `npm install`
2. `npm run dev -- --open`

### Using the application
You should see an input for a local filepath. Enter something in (like, for instance, `/Users/my.user/Documents/Personal/Test`) and hit the "Analyze" button!
You can drag and drop files and directories into the chat window context to ask questions about it.