# Pterodactyl Setup Guide

## Prerequisites
Ensure your Pterodactyl server is configured with:
- **Docker Image**: Python 3.13+
- **Startup Command**: `/usr/local/bin/python /home/container/main.py`
- **Auto-Update**: Enabled (to pull latest from git)

## Setup Steps

### 1. Provide Bot Token (3 Methods - Choose One)

The bot supports three methods to load your bot token in this priority order:

#### Method 1: Environment Variable (Recommended for Pterodactyl)
1. In Pterodactyl panel, go to **Startup** settings
2. Add environment variable: `DISCORD_TOKEN=your_bot_token_here`
3. Save and restart

#### Method 2: Token File (for Local Testing)
1. Create file `token.txt` with your Discord bot token
2. Upload to Pterodactyl file manager (root directory)
3. Or place in local directory for testing

#### Method 3: Hardcoded (Not Recommended - Security Risk)
Edit `main.py` line 17:
```python
HARDCODED_TOKEN = "your_bot_token_here"
```
⚠️ **Warning**: This exposes your token in the repository!

### 2. Verify File Structure
The server should have:
```
/home/container/
├── main.py
├── config.py
├── requirements.txt
├── token.txt          (← Create this)
├── cogs/
├── data/              (← Created automatically)
└── utils/
```

### 3. Install Dependencies
If dependencies aren't auto-installed:
```
pip install -U --prefix .local -r requirements.txt
```

### 4. Start the Server
1. Go to Console tab
2. Click "Start" button
3. Wait for full startup (should see "Bot is ready" message)
4. If crashed, check console output for errors

## Troubleshooting

### "token.txt not found"
- Upload `token.txt` to the file manager
- Ensure file is in root directory (`/home/container/`)
- Check file is readable

### "ModuleNotFoundError: No module named 'discord'"
- Dependencies didn't install
- Re-install: `pip install -U --prefix .local -r requirements.txt`
- Restart the server

### "Server keeps crashing"
- Check the console logs for specific error messages
- Verify `token.txt` exists and has valid token
- Ensure all files are present (no truncated uploads)

## Commands Available
- `/join_queue` - Join the match queue
- `/leave_queue` - Leave the queue
- `/queue` - Show current queue
- `/start_match` - Start a 2-player match
- `/matches` - List recent matches
- `/leaderboard [page]` - Show ranked leaderboard with pagination
