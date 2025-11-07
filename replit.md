# GitHub AI Automation Tool

## Overview
A cloud-based GitHub automation service that responds to @my-tool mentions in issue comments. The system uses AI (LLM with tool calling) to analyze issues, edit codebase files intelligently, and automatically create pull requests.

**Status**: Initial setup (November 7, 2025)

## Architecture

### Frontend
- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS + Shadcn UI components
- **Features**: Configuration dashboard, job status tracking, API key management

### Backend
- **Framework**: Flask (Python)
- **API**: RESTful endpoints for frontend + GitHub webhook handler
- **AI Integration**: OpenAI for code analysis and generation
- **GitHub Integration**: PyGithub for repository operations and PR creation

## Project Structure
```
/
├── frontend/          # Next.js application
│   ├── src/
│   │   ├── app/      # App router pages
│   │   ├── components/  # React components (Shadcn UI)
│   │   ├── lib/      # Utilities and API clients
│   │   └── types/    # TypeScript definitions
│   └── package.json
├── backend/           # Flask API
│   ├── app.py        # Main Flask application
│   ├── services/     # Business logic (GitHub, LLM, PR creation)
│   ├── routes/       # API endpoints
│   └── requirements.txt
└── replit.md         # This file
```

## How It Works
1. User comments `@my-tool` on a GitHub issue
2. GitHub webhook sends event to Flask backend
3. Backend fetches issue details and repository code
4. LLM analyzes issue and determines necessary code changes
5. AI uses tool calling to edit specific files
6. System creates a PR with the changes
7. Dashboard shows job status and history

## Environment Variables Required
- `OPENAI_API_KEY` - OpenAI API key for LLM
- `GITHUB_TOKEN` - GitHub personal access token for API access
- `WEBHOOK_SECRET` - GitHub webhook secret for verification
- `SESSION_SECRET` - Already configured

## Recent Changes
- **2025-11-07**: Initial project setup and architecture planning

## User Preferences
- Backend in Python (Flask)
- Frontend in Next.js with TypeScript
- Use Tailwind CSS and Shadcn UI library
- Focus on cloud-based agent automation
