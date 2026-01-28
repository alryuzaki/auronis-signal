# Financial Signals & Subscription Bot

This is a Telegram Bot built with Python (`python-telegram-bot` v20+) designed for managing subscriptions to financial signals (Stocks, Crypto, Indices). It includes a role-based access system, package management, and GitHub Actions integration for automated maintenance tasks (cron).

## Features

*   **Role Management**: Super Admin, Admin, Member, Viewer.
*   **Subscriptions**: Create packages, subscribe users, auto-expire.
*   **Automation**:
    *   Auto-remind 3 days before expiry.
    *   Auto-kick expired users from managed groups.
    *   Scheduled announcements.
*   **Database**: SQLite (`bot_data.db`).

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd BotInvest
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration**:
    *   Copy `.env.example` to `.env`.
    *   Fill in your details:
        ```env
        TELEGRAM_BOT_TOKEN=12345:YourTokenHere
        ADMIN_USER_ID=123456789
        MANAGED_GROUP_ID=-100123456789  # ID of the VIP Group to manage (comma separated for multiple)
        ```

4.  **Run the Bot (Local/VPS)**:
    This runs the main listener for user commands.
    ```bash
    python main.py
    ```

## GitHub Actions & Cron

The project includes a workflow `.github/workflows/bot-cron.yml` that runs `cron_tasks.py` daily.

**Important Note on SQLite Persistence**:
Since GitHub Actions runners are ephemeral (files are lost after the run), using a local SQLite file (`bot_data.db`) inside GitHub Actions requires a strategy to persist data:
1.  **Self-Hosted Runner**: Run the action on your own server where the file exists.
2.  **External Storage**: Modify the workflow to Download the DB from S3/FTP before running, and Upload it back after running.
3.  **Remote Database**: Switch `database.py` to use PostgreSQL/MySQL if using standard GitHub Runners.

## Commands

**User**:
*   `/start` - Register.
*   `/myprofile` - Check status.
*   `/subscribe <id>` - Subscribe to a package.
*   `/listpackages` - View packages.

**Super Admin**:
*   `/createrole <name>`
*   `/createpackage <name> <price> <days>`
*   `/addmember <id> <name> <role>`
*   `/announce <message>`
*   `/schedule <daily|once> <time> <message>`
