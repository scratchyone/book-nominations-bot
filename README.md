# book-nominations-bot

A Discord bot that tracks book nominations via reactions.

## Running with Docker

### 1. Create a `.env` file

```
BOT_TOKEN=your_discord_bot_token_here
```

### 2. Build

```bash
docker buildx build -t book-nominations-bot .
```

### 3. Run

```bash
docker compose up -d
```

To stop:

```bash
docker compose down
```
