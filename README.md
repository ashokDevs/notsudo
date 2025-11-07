# GitHub AI Automation Tool

A cloud-based service that automates code changes in response to GitHub issue comments. Simply mention `@my-tool` in any issue comment, and the AI will analyze the issue, make intelligent code changes, and create a pull request.

## Features

- **AI-Powered Code Analysis**: Uses OpenAI's GPT-4 with function calling to understand issues and plan code changes
- **Automated PR Creation**: Automatically creates pull requests with proposed fixes
- **Web Dashboard**: Configure API keys and monitor automation jobs
- **GitHub Integration**: Webhook-based event handling for real-time responses
- **Smart File Selection**: Intelligently selects relevant files from the codebase for analysis

## Architecture

### Frontend
- Next.js 14 with TypeScript
- Tailwind CSS + Shadcn UI components
- Configuration dashboard for API credentials
- Job history tracking

### Backend
- Flask API (Python)
- GitHub webhook handler
- OpenAI integration with tool calling
- PyGithub for repository operations

## Setup Instructions

### 1. Configure API Keys

You'll need:
- **GitHub Personal Access Token**: Create at https://github.com/settings/tokens
  - Required scopes: `repo`, `workflow`
- **OpenAI API Key**: Get from https://platform.openai.com/api-keys

### 2. Configure the Dashboard

1. Open the web application
2. Go to the "Configuration" tab
3. Enter your GitHub token and OpenAI API key
4. Click "Save Configuration"

### 3. Set Up GitHub Webhook

1. Go to the "Webhook Setup" tab in the dashboard
2. Click "Get Webhook URL" to generate your webhook URL
3. Go to your GitHub repository → Settings → Webhooks
4. Click "Add webhook"
5. Paste the webhook URL
6. Select "Let me select individual events"
7. Check "Issue comments"
8. Click "Add webhook"

### 4. Use the Tool

1. Create or open a GitHub issue in your repository
2. Add a comment mentioning `@my-tool` with instructions
3. The AI will:
   - Analyze the issue and codebase
   - Determine necessary changes
   - Create a new branch
   - Apply code changes
   - Open a pull request

Example comment:
```
@my-tool Please fix the login validation bug mentioned in this issue
```

## How It Works

1. **Webhook Trigger**: GitHub sends a webhook when someone comments on an issue with `@my-tool`
2. **Code Fetching**: The backend fetches relevant files from the repository
3. **AI Analysis**: OpenAI analyzes the issue and suggests changes using function calling
4. **Branch Creation**: A new branch is created from the main branch
5. **File Updates**: The AI-suggested changes are committed to the new branch
6. **PR Creation**: A pull request is opened with all the changes

## API Endpoints

- `POST /api/config` - Save API configuration
- `GET /api/config` - Check if credentials are configured
- `POST /api/webhook` - GitHub webhook handler
- `GET /api/jobs` - Get job history
- `GET /health` - Health check

## Tech Stack

**Frontend:**
- Next.js 14
- TypeScript
- Tailwind CSS
- Shadcn UI
- React

**Backend:**
- Python 3.11
- Flask
- PyGithub
- OpenAI Python SDK
- Flask-CORS

## Security Notes

- API keys are stored in temporary server storage (not persisted)
- For production use, implement proper secret management
- Configure webhook signature verification for enhanced security
- Use HTTPS for all webhook endpoints

## Development

The application runs on:
- Frontend: `http://localhost:5000`
- Backend: `http://localhost:8000`

Both servers start automatically when you run the project.

## Limitations

- Maximum 15 files analyzed per issue (configurable)
- File content limited to 2000 characters for AI context
- Requires manual PR review and merge

## Future Enhancements

- Database for persistent job history
- Webhook signature verification
- Multiple LLM provider support
- Pre-PR approval workflow
- Code diff preview in dashboard
