import os
import datetime
import discord
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
CREDS_FILE = os.getenv("GOOGLE_CREDENTIALS")

# set up Google Sheets client
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(CREDS_FILE, scopes=scopes)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).sheet1  # assumes first sheet

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    # ignore bots + non-DMs
    if message.author.bot or not isinstance(message.channel, discord.DMChannel):
        return

    parts = message.content.strip().split(maxsplit=1)
    if len(parts) != 2 or not parts[0].replace('.', '', 1).isdigit():
        await message.channel.send("Use: `<amount> <description>`, e.g. `12.50 lunch`")
        return

    amount, desc = parts
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [now, amount, desc]
    sheet.append_row(row)
    await message.channel.send(f"✅ Logged: {amount} for `{desc}` at {now}")

client.run(DISCORD_TOKEN)
