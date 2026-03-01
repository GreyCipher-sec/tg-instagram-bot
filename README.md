# Instabridge

Automatically detects Instagram links posted in a Telegram group and re-uploads the photos or videos natively.

---

## Project Structure

```
instagram_telegram_bot/
├── bot.py
├── requirements.txt
├── .env.example
├── .env
├── .gitignore
└── README.md
```

---

## Local Setup

### 1. Create a Telegram Bot
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** you receive

### 2. Disable privacy mode
In BotFather: `/setprivacy` → your bot → **Disable**
This lets the bot read all group messages, not just commands.

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Configure secrets
```
cp .env.example .env
# Edit .env and fill in your TELEGRAM_BOT_TOKEN
```

### 5. Run
```
python bot.py
```

---

## Self-Hosting

```
# Install Python & pip
sudo apt update && sudo apt install python3 python3-pip -y

# Clone your repo
git clone https://github.com/GreyCipher-sec/tg-instagram-bot.git
cd tg-instagram-bot

# Install dependencies
pip3 install -r requirements.txt

# Create your .env
cp .env.example .env
nano .env  # fill in your token

# Run as a persistent service (see systemd section below)
```

### Run as a persistent systemd service

```
sudo nano /etc/systemd/system/instabot.service
```

```
[Unit]
Description=Instagram Telegram Bot
After=network.target

[Service]
WorkingDirectory=/home/ubuntu/YOUR_REPO
ExecStart=/usr/bin/python3 bot.py
EnvironmentFile=/home/ubuntu/YOUR_REPO/.env
Restart=always
User=ubuntu

[Install]
WantedBy=multi-user.target
```

```
sudo systemctl enable instabot
sudo systemctl start instabot
sudo systemctl status instabot   # check it's running
journalctl -u instabot -f        # live logs
```

## Optional: Instagram Cookies (for private posts or rate limiting)

1. Install the **"Get cookies.txt LOCALLY"** browser extension
2. Log in to Instagram and export cookies to a file
3. Set the path in `.env`:
   ```
   INSTAGRAM_COOKIES_FILE=/path/to/instagram_cookies.txt
   ```
