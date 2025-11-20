from flask import Flask, request, render_template
from concurrent.futures import ThreadPoolExecutor
from config import config
import os
import logging
from GitHub_Event_Handler.processIssueEvents import process_issue_event
from GitHub_Event_Handler.processPushEvents import process_push_event
from GitHub_Event_Handler.processInstallationEvents import process_installation_event
from Issue_Indexer.getAllIssues import fetch_repository_issues
from Data_Storage.dbOperations import insert_issue_to_db, create_table_if_not_exists, delete_table

# Initialize App
app = Flask(__name__)

# Load Config
env_name = os.getenv('FLASK_ENV', 'default')
app.config.from_object(config[env_name])

# Configure logging
logging.basicConfig(
    level=logging.INFO if not app.config['DEBUG'] else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ThreadPool for concurrent webhook processing
executor = ThreadPoolExecutor(max_workers=app.config['MAX_WORKERS'])


@app.route('/', methods=['GET'])
def homepage():
    """
    Serves the INSIGHT homepage with tool information
    
    Returns:
        HTML page with tool description, features, architecture, and API documentation
    """
    logging.info(f"Homepage accessed from {request.remote_addr}")
    return render_template('homepage.html')


@app.route('/', methods=['POST'])
def api_git_msg():
    """
    Main webhook endpoint for GitHub events
    
    Handles:
    - push events: Triggers Knowledge Base updates
    - installation events: Sets up database and indexes repository
    - issue events: Performs bug localization
    """
    logging.info(f"Webhook received from {request.remote_addr}")
    if request.headers['Content-Type'] == 'application/json':
        data = request.json
        event = request.headers.get('X-GitHub-Event', '')
        action = data.get('action', '')
        logging.info(f"Event: {event}, Action: {action}")

        if event == 'push':
            # Handle push events for automatic knowledge base updates
            try:
                repo_full_name = data['repository']['full_name']
                ref = data.get('ref', '')
                
                # Only process main/master branch pushes
                if not (ref.endswith('/main') or ref.endswith('/master')):
                    return f"Ignoring push to non-main branch: {ref}", 200
                
                # Process push in background
                executor.submit(process_push_event, repo_full_name, data)
                
                return "Push event accepted for processing", 200
            except Exception as e:
                logging.error(f"Failed to handle push event: {e}", exc_info=True)
                return "Push event handling failed", 500

        elif event == 'installation' and action == 'created':
            logging.info(f"Installation event received with action: {action}")
            installed_repos = data['repositories']
            logging.info(f"Number of repositories to install: {len(installed_repos)}")
            
            for repo in installed_repos:
                repo_full_name = repo['full_name']
                default_branch = repo.get('default_branch', 'master')
                # Process in background
                executor.submit(process_installation_event, repo_full_name, default_branch, 'created')
            
            return "Installation event accepted for processing", 200

        elif event == 'installation_repositories' and action == 'added':
            logging.info(f"Installation repositories added event received")
            added_repos = data.get('repositories_added', [])
            logging.info(f"Number of repositories added: {len(added_repos)}")
            
            for repo in added_repos:
                repo_full_name = repo['full_name']
                default_branch = repo.get('default_branch', 'master')
                # Process in background
                executor.submit(process_installation_event, repo_full_name, default_branch, 'added')
            
            return "Installation repositories added event accepted for processing", 200

        elif event == 'installation' and action == 'deleted':
            removed_repos = data['repositories']
            for repo in removed_repos:
                repo_full_name = repo['full_name']
                # Process in background
                executor.submit(process_installation_event, repo_full_name, None, 'deleted')
            
            return "Uninstallation event accepted for processing", 200

        elif event == 'issues':
            repo_full_name = data['repository']['full_name']
            issue_number = data['issue']['number']
            issue_title = data['issue']['title']
            issue_body = data['issue']['body']
            issue_creation_time = data['issue']['created_at']  
            issue_url = data['issue']['html_url']
            issue_labels = [label['name'] for label in data['issue'].get('labels', [])]
            default_branch = data['repository'].get('default_branch', 'main')

            input_issue = {
                'issue_number': issue_number,
                'issue_title': issue_title,
                'issue_body': issue_body,
                'created_at': issue_creation_time,
                'issue_url': issue_url,
                'issue_labels': issue_labels,
                'issue_branch': default_branch
            }

            executor.submit(process_issue_event, repo_full_name, input_issue, action)

            return "Issue event handled", 200
        else:
            return "Not a relevant event, no action required.", 200
    else:
        return "415 Unsupported Media Type ;)", 415


if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'], port=app.config['PORT'])


# https://github.com/apps/sprint-issue-report-assistant
# https://github.com/apps/issue-plugin
