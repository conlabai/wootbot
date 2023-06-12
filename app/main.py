import os
import asyncpg
import httpx
import asyncio
import logging
from fastapi import FastAPI

# Get the log level from the environment variable
log_level = os.getenv('LOG_LEVEL', 'INFO')

# Convert the log level to an integer
numeric_level = getattr(logging, log_level.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError(f'Invalid log level: {log_level}')

# Set the log level
logging.basicConfig(level=numeric_level)

class ConversationState:
    async def setup_db(self):
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                logging.debug(f"Connecting to database... (attempt {attempt})")
                self.conn = await asyncpg.connect(
                    user=os.getenv('POSTGRES_USER'),
                    password=os.getenv('POSTGRES_PASSWORD'),
                    database=os.getenv('POSTGRES_DB'),
                    host=os.getenv('POSTGRES_HOST')
                )
                logging.debug("Connected to database.")
                
                # Creating states table
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS states (
                        conversation_id INT PRIMARY KEY,
                        state TEXT
                    )
                ''')
                logging.debug("States table created.")
                
                # Creating messages table
                await self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        conversation_id INT,
                        message TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                logging.debug("Messages table created.")
                
                break
            except Exception as e:
                logging.error(f"Error setting up database: {e}")
                if attempt == max_attempts:
                    logging.error("Max attempts reached. Shutting down.")
                    raise
                else:
                    logging.debug("Retrying in 5 seconds...")
                    await asyncio.sleep(5)


    async def get_state(self, conversation_id):
        try:
            result = await self.conn.fetchrow('SELECT state FROM states WHERE conversation_id = $1', conversation_id)
            return result[0] if result else 'initial'
        except Exception as e:
            logging.error(f"Error getting state: {e}")
            return 'initial'

    async def set_state(self, conversation_id, state):
        try:
            await self.conn.execute('INSERT INTO states (conversation_id, state) VALUES ($1, $2) ON CONFLICT (conversation_id) DO UPDATE SET state = $2', conversation_id, state)
        except Exception as e:
            logging.error(f"Error setting state: {e}")

    async def save_message(self, conversation_id, message, creeated_at):
        try:
            await self.state_model.conn.execute('''
                INSERT INTO messages (conversation_id, message, created_at) VALUES ($1, $2, $3)
            ''', conversation_id, message)
        except Exception as e:
            logging.error(f"Error saving message: {e}")



class ChatActions:
    def __init__(self, state_model):
        self.state_model = state_model
        self.chatwoot_url = os.getenv('CHATWOOT_URL')
        self.chatwoot_api_token = os.getenv('CHATWOOT_API_TOKEN')
        self.greeting_message = os.getenv('GREETING_MESSAGE', 'Hello, I am Wootbot. I am here to help you with your queries. How can I help you today?')
        self.handoff_message = os.getenv('HANDOFF_MESSAGE', 'Transferring you to a human agent. Please wait...')

    async def handle_event(self, event):
        try:
            # Extract event parameters
            message_type = event.get('message_type')
            event_type = event.get('event')
            message_status = event.get('conversation', {}).get('status')
            conversation_id = event.get('conversation', {}).get('id')
            account_id = event.get('account', {}).get('id')
            first_message_dict = event.get('conversation', {}).get('messages', [{}])[0]  # Get first message or default to empty dict
            message = first_message_dict.get('content')
            created_at = first_message_dict.get('created_at')
            
            # Check that it's an incoming message and conversation is pending   
            if message_type != "incoming" or event_type != "message_created" or message_status != "pending":
                return {"message": "Invalid event"}

            # Check the current state of the conversation
            state = await self.state_model.get_state(conversation_id)

            # If the conversation is in the initial state, send a greeting
            if state == 'initial':
                await self.send_greeting(conversation_id, account_id)
                await self.state_model.set_state(conversation_id, 'greeted')
            # If the conversation is in the greeted or handoff state, send a handoff message
            elif state == 'greeted' or state == 'handoff':
                await self.state_model.save_message(conversation_id, message, created_at)
                await self.send_handoff_message(conversation_id, account_id)
                await self.execute_handoff_action(conversation_id, account_id)
                await self.state_model.set_state(conversation_id, 'handoff')
            else:
                # If the conversation is in any other state, ignore the message
                return {"message": "Invalid state"}

            return {}
        except Exception as e:
            logging.error(f"Error handling event: {e}")

    async def send_greeting(self, conversation_id, account_id):
        try:
            url = f'{self.chatwoot_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages'
            headers = {'api_access_token': self.chatwoot_api_token}
            data = {'content': self.greeting_message}
            async with httpx.AsyncClient() as client:
                await client.post(url, headers=headers, json=data)
        except Exception as e:
            logging.error(f"Error sending greeting: {e}")

    async def send_handoff_message(self, conversation_id, account_id):
        try:
            url = f'{self.chatwoot_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages'
            headers = {'api_access_token': self.chatwoot_api_token}
            data = {'content': self.handoff_message}
            async with httpx.AsyncClient() as client:
                await client.post(url, headers=headers, json=data)
        except Exception as e:
            logging.error(f"Error sending handoff message: {e}")

    async def execute_handoff_action(self, conversation_id, account_id):
        try:
            url = f'{self.chatwoot_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/toggle_status'
            headers = {'api_access_token': self.chatwoot_api_token}
            data = {'status': 'open'}
            async with httpx.AsyncClient() as client:
                res = await client.post(url, headers=headers, json=data)
                if res.status_code != 200:
                    logging.error(f"Error executing handoff action: {res.status_code}")
        except Exception as e:
            logging.error(f"Error executing handoff action: {e}")

app = FastAPI()
state_model = ConversationState()
chat_actions = ChatActions(state_model)

@app.on_event("startup")
async def startup_event():
    await state_model.setup_db()

@app.post("/")
async def handle_event(event: dict):
    logging.debug(f"Received event: {event}")
    result = await chat_actions.handle_event(event)
    logging.debug(f"Result: {result}")
    return result


