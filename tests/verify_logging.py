import sys
import os
import time
from unittest.mock import MagicMock, patch

# Add current dir to path so we can import app modules
sys.path.append(os.getcwd())

# Mock the database dependencies before importing worker
with patch('app.workers.worker.save_link'), \
     patch('app.workers.worker.get_queue_provider'):
    
    from app.workers import worker
    from app.core import metrics

    # Mock external services
    worker.jira = MagicMock()
    worker.jira.create_issue.return_value.key = "TEST-123"
    worker.jira.create_issue.return_value.fields.priority.name = "High"
    worker.jira.create_issue.return_value.fields.assignee.displayName = "Test User"
    worker.jira.create_issue.return_value.fields.created = "2023-01-01"
    
    worker.slack = MagicMock()
    worker.slack.chat_postMessage.return_value = {"ts": "123456"}

    # Mock metrics logging to verify call, but also let it write to file to check CSV
    # We want to check if it writes to CSV, so we won't mock log_metric, just observe side effect
    # OR we can inspect the CSV file after.
    
    # Ensure CSV is clean-ish or we just look for our specific entry
    test_timestamp = time.time()
    
    data = {
        "channel_id": "C123",
        "user_id": "U123",
        "title": "Test Ticket",
        "description": "Test Desc",
        "project_key": "TEST",
        "timestamp": test_timestamp
    }

    print("Executing create ticket...")
    worker.execute_create_ticket(data)
    print("Execution complete.")

    # Check metrics file
    if os.path.exists(metrics.LOG_FILE):
        with open(metrics.LOG_FILE, 'r') as f:
            content = f.read()
            if "execution_create_ticket" in content and "TEST-123" in content:
                print("SUCCESS: Log entry found in CSV.")
            else:
                print("FAILURE: Log entry NOT found in CSV.")
                print("CSV Content:", content)
    else:
        print("FAILURE: Log file not found.")
