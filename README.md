# NexoAI Discord Bot (Python 3.11 + LiteLLM)

A feature-rich Discord bot for hosting owners and support communities.

## Features

- AI chat with provider fallback via LiteLLM (`/ai`)
- AI utilities: summarize, translate, rewrite, code generation
- Per-user persona setting (`/setpersona`)
- Channel-based auto AI replies with memory
- Guild-level custom system prompt
- Support ticket modal (`/ticket`)
- Hosting/status commands (`/ping`, `/uptime`)
- Server and user info commands
- Admin commands for setup and announcements
- Moderation tools: purge, timeout, untimeout, warn
- Basic anti-scam message filter
- SQLite persistence for settings and conversation history

## Requirements

- Python 3.11
- A Discord bot token
- At least one AI API key: Groq, OpenRouter, or Cerebras

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create your config file:

```bash
copy config.yaml.example config.yaml
```

3. Edit `config.yaml`:

- `discord.token`: your Discord bot token
- `groq.api_key` / `openrouter.api_key` / `cerebras.api_key`: add one or more keys
- `llm.fallback_order`: provider order when one fails
- Optional: model, prefix, owner IDs, system prompt, database path, presence

4. Run:

```bash
python bot.py
```

## Recommended Discord Bot Settings

- Enable intents in Discord Developer Portal:
  - MESSAGE CONTENT INTENT
  - SERVER MEMBERS INTENT
- Give bot permissions:
  - Send Messages
  - Read Message History
  - Manage Messages (for purge)
  - Moderate Members (for timeout)

## Key Slash Commands

### Member Commands (everyone)

- `/ai prompt:<text>`
- `/summarize text:<text>`
- `/translate target_language:<lang> text:<text>`
- `/rewrite style:<style> text:<text>`
- `/code language:<lang> request:<task>`
- `/setpersona persona:<style>`
- `/agent name:<preset>`
- `/agents`
- `/clearhistory`
- `/helpme`
- `/ping`
- `/uptime`
- `/serverinfo`
- `/membercount`
- `/userinfo [user]`
- `/ticket`

### Extra AI Prefix (no slash)

- Type: `@nexoai your question`
- You can change this in `config.yaml` under `bot.mention_prefixes`.
- In DMs, you can just message the bot normally and it will answer.
- You can attach files in DM/server AI chats; text files are read, zip files are extracted to disk and analyzed.

### Rotating Status

Configure under `bot.rotating_statuses` in `config.yaml`:

- `watching` -> `hosting support | /helpme`
- `custom` -> `made by Alok_Playzz`
- `playing` -> `@mention , / , ! .`

### AI Fallback Order

If one provider key/model fails, bot auto-tries next provider:

- `groq`
- `openrouter`
- `cerebras`

Configure in `config.yaml`:

```yaml
llm:
  fallback_order:
    - "groq"
    - "openrouter"
    - "cerebras"
```

### Admin Commands

- `/setaichannel channel:<#channel>`
- `/toggleautoreply enabled:true|false`
- `/setsupportchannel channel:<#channel>`
- `/setsystemprompt prompt:<text>`
- `/announce channel:<#channel> message:<text>`

### Moderation Commands

- `/purge amount:<1-100>`
- `/timeout member:<user> minutes:<n> [reason]`
- `/untimeout member:<user>`
- `/warn member:<user> reason:<text>`

## Notes

- Never commit `config.yaml` with real tokens (it is listed in `.gitignore`).
- Use `config.yaml.example` as a safe template for sharing or version control.
- Conversation context is stored in the database path set under `bot.database_path` (default: `nexoai.db`).
- If slash commands do not appear, run the bot and wait a minute, or run `!sync` as the bot owner.
