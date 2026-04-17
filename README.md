# Instabridge

Automatically detects Instagram links posted in a Telegram group and re-uploads the photos or videos natively.

---

## Project Structure

```
tg-instagram-bot/
├── main.py
├── Dockerfile
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

### 2. Disable Privacy Mode

In BotFather: `/setprivacy` → your bot → **Disable**
This lets the bot read all group messages, not just commands.

### 3. Install Dependencies

```
pip install -r requirements.txt
```

### 4. Configure Secrets

```
cp .env.example .env
# Edit .env and fill in your values
```

### 5. Run

```
python main.py
```

---

## Self-Hosting with systemd

```
# Install Python & pip
sudo apt update && sudo apt install python3 python3-pip -y

# Clone the repo
git clone https://github.com/GreyCipher-sec/tg-instagram-bot.git
cd tg-instagram-bot

# Install dependencies
pip3 install -r requirements.txt

# Create your .env
cp .env.example .env
nano .env
```

Create the service file:

```
sudo nano /etc/systemd/system/instabot.service
```

```ini
[Unit]
Description=Instagram Telegram Bot
After=network.target

[Service]
WorkingDirectory=/home/user/tg-instagram-bot
ExecStart=/home/user/tg-instagram-bot/.venv/bin/python main.py
EnvironmentFile=/home/user/tg-instagram-bot/.env
Restart=always
User=user

[Install]
WantedBy=multi-user.target
```

> `ExecStart` must point to the virtualenv's Python binary, not the system one.

Enable and start:

```
sudo systemctl enable instabot
sudo systemctl start instabot
sudo systemctl status instabot
journalctl -u instabot -f   # live logs
```

---

## Self-Hosting with Docker

Build the image:

```
docker build -t instabot .
```

Run with your `.env` file:

```
docker run -d --name instabot --env-file .env instabot
```

Check status and logs:

```
docker ps
docker logs -f instabot
```

Stop and remove:

```
docker stop instabot && docker rm instabot
```

> Make sure `.env` is filled in before running — the bot will fail
> to start without a valid `TELEGRAM_BOT_TOKEN`.

---

## Optional: Instagram Cookies (Private Posts & Rate Limiting)

1. Install the **"Get cookies.txt LOCALLY"** browser extension
2. Log in to Instagram and export cookies to a file
3. Set the path in `.env`:

```
INSTAGRAM_COOKIES_FILE=/path/to/instagram_cookies.txt
```

> The authenticated account must follow the private profile for
> private post downloads to work.
