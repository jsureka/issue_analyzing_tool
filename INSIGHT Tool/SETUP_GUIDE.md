# INSIGHT Tool - Setup and Running Guide

This guide provides step-by-step instructions for setting up and running the INSIGHT tool locally with ngrok tunneling for GitHub webhook integration.

## Prerequisites

- Python 3.8 or higher
- ngrok account and authentication token
- GitHub App credentials (App ID, Client ID, Private Key)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-repo/insight-tool.git
cd insight-tool
```

### 2. Install Dependencies

```bash
cd "INSIGHT Tool"
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the `INSIGHT Tool` directory with the following variables:

```bash
GITHUB_PRIVATE_KEY=your_github_app_private_key
GITHUB_APP_ID=your_github_app_id
CLIENT_ID=your_github_client_id
POOL_PROCESSOR_MAX_WORKERS=4
```

### 4. Set Up ngrok

#### Option A: Using the Setup Script (Windows)

Double-click `setup_ngrok.bat` or run:

```bash
setup_ngrok.bat
```

This will configure your ngrok authentication token automatically.

#### Option B: Manual Configuration

Install ngrok from [ngrok.com/download](https://ngrok.com/download) and configure your authentication token:

```bash
ngrok config add-authtoken YOUR_NGROK_TOKEN
```

**Important:** Make sure you have ngrok version 3.7.0 or higher. Update if needed:

```bash
ngrok update
```

Or download the latest version from [ngrok.com/download](https://ngrok.com/download).

### 5. Start the Application

You need to run two commands in separate terminals:

#### Terminal 1: Start ngrok Tunnel

**Option A: Using the Start Script (Windows)**

Double-click `start_ngrok.bat` or run:

```bash
start_ngrok.bat
```

**Option B: Manual Command**

```bash
ngrok http 5000
```

**Copy the forwarding URL** displayed by ngrok (e.g., `https://xxxx-xx-xx-xx-xx.ngrok.io`)

#### Terminal 2: Start Flask Application

```bash
cd "INSIGHT Tool"
python main.py
```

The application will start on `http://127.0.0.1:5000`

### 6. Access the Homepage

Open your browser and navigate to:

- **Local:** http://127.0.0.1:5000/
- **ngrok:** Use the ngrok forwarding URL from Terminal 1

You should see the INSIGHT homepage with information about the tool, features, architecture, and API documentation.

### 7. Configure GitHub Webhook

1. Go to your GitHub repository
2. Navigate to **Settings → Webhooks → Add Webhook**
3. Configure the webhook:
   - **Payload URL:** Paste your ngrok forwarding URL (e.g., `https://xxxx-xx-xx-xx-xx.ngrok.io`)
   - **Content type:** `application/json`
   - **Events:** Select:
     - Issues
     - Issue comments
     - Push events
4. Click **Add webhook**

### 8. Test INSIGHT

Create a new issue in your GitHub repository and watch INSIGHT analyze it automatically!

## Troubleshooting

### ngrok URL Changes

**Problem:** The ngrok URL changes every time I restart ngrok (free tier).

**Solution:** Update your GitHub webhook URL with the new ngrok forwarding URL each time you restart ngrok. Consider upgrading to a paid ngrok plan for a static URL.

### Port Already in Use

**Problem:** Error message "Address already in use" when starting Flask.

**Solution:**

- Check if another application is using port 5000
- Kill the process using the port:
  ```bash
  # Windows
  netstat -ano | findstr :5000
  taskkill /PID <PID> /F
  ```

### Webhook Not Triggering

**Problem:** GitHub webhooks are not being received by the application.

**Solution:**

- Verify ngrok tunnel is active and running
- Check that the ngrok forwarding URL is correctly configured in GitHub webhook settings
- Look at the webhook delivery history in GitHub Settings → Webhooks
- Check Flask application logs for incoming requests

### Authentication Errors

**Problem:** GitHub API authentication failures.

**Solution:**

- Verify your GitHub App credentials in the `.env` file
- Ensure the private key is correctly formatted (including newlines)
- Check that your GitHub App has the necessary permissions:
  - Issues: Read & Write
  - Contents: Read
  - Webhooks: Read & Write

### ngrok Version Too Old

**Problem:** Error message "Your ngrok-agent version is too old".

**Solution:**

- Update ngrok to version 3.7.0 or higher:
  ```bash
  ngrok update
  ```
- Or download the latest version from [ngrok.com/download](https://ngrok.com/download)

### Static Assets Not Loading

**Problem:** CSS or images not displaying on the homepage.

**Solution:**

- Verify the `static` directory structure exists:
  ```
  INSIGHT Tool/
  ├── static/
  │   ├── css/
  │   │   └── style.css
  │   └── images/
  │       ├── logo.png
  │       └── architecture.png
  ```
- Check Flask application logs for 404 errors
- Clear your browser cache

## Development Tips

### Viewing Logs

The Flask application logs all requests. Watch the Terminal 2 output to see:

- Homepage access requests
- Webhook events received
- Processing status

### Testing Locally

You can test the application locally without ngrok:

1. Start only the Flask application (Terminal 2)
2. Access the homepage at http://127.0.0.1:5000/
3. Test webhook endpoint with curl or Postman:
   ```bash
   curl -X POST http://127.0.0.1:5000/ \
     -H "Content-Type: application/json" \
     -H "X-GitHub-Event: ping" \
     -d '{"action":"opened","repository":{"full_name":"test/repo"}}'
   ```

### Stopping the Application

- **Flask:** Press `Ctrl+C` in Terminal 2
- **ngrok:** Press `Ctrl+C` in Terminal 1

## Next Steps

- Explore the API documentation on the homepage
- Customize the ML models by updating paths in `.env`
- Extend INSIGHT with new features (see README.md)
- Deploy to production with Gunicorn and Nginx

## Support

For issues, questions, or contributions:

- Open an issue on [GitHub](https://github.com/sea-lab-wm/sprint_issue_report_assistant_tool/issues)
- Contact the contributors (see homepage footer)

## License

INSIGHT is open source and licensed under the MIT License.
