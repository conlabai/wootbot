# Simple Agent Bot for Chatwoot

## Introduction

Simple Agent Bot is a FastAPI based application integrated with Chatwoot. Upon receiving a new message, the bot sends a greeting, after receiving second message answers with a notification about transferring the conversation to a human agent and change the dialogue status in Chatwoot to 'Open'.

## Adding WootBot to Chatwoot Docker Stack

To integrate WootBot with your system, add WootBot to Chatwoot stack. 

```yaml
version: '3.8'
services:

  # All Chatwoot services here

  wootbot:
    image: conlab/wootbot:latest
    environments:
      - GREETING_MESSAGE=Hello, I am Wootbot. I am here to help you with your queries. How can I help you today?
      - HANDOFF_MESSAGE=Transferring you to a human agent. Please wait.
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=paste_wootbot_password_here
      - POSTGRES_DB=wootbot-production
      - POSTGRES_HOST=wootbot-db
      - CHATWOOT_URL=paste_chatwoot_url_here
      - CHATWOOT_API_TOKEN=paste_your_agent_bot_token_here
    depends_on:
      - wootbot-db
  wootbot-db:
    image: postgres:14.4
    environments:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=paste_wootbot_password_here
      - POSTGRES_DB=wootbot-production
      - POSTGRES_HOST=wootbot-db
    volumes:
      - wootbot-db-data:/var/lib/postgresql/data/
volumes:
  # Chatwoot volumes here
  wootbot-db-data:
```

The bot will be accessible via http://wootbot:8080 inside Chatwoot docker network

## Environment Setup:

- `GREETING_MESSAGE`: Custom greeting message dispatched by the bot.
- `HANDOFF_MESSAGE`: Message delivered when the bot is handing off to a human agent.
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`: Credentials for your PostgreSQL setup.
- `CHATWOOT_URL`: Your Chatwoot instance URL.
- `CHATWOOT_API_TOKEN`: The API token you obtained from setting up the agent bot in Chatwoot

## Create Agent Bot in Chatwoot:

First, you need to create an agent bot within Chatwoot. Once you've set it up, you can then obtain the agent bot API. For detailed instructions on setting this up, please refer to the official Chatwoot documentation [here](https://www.chatwoot.com/docs/product/others/agent-bots).


### Select WootBot in Chatwoot Inbox:

After integrating WootBot into your system, return to Chatwoot and select the WootBot as your agent for the desired inbox.

## Licence

MIT
