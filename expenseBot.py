import discord
from discord import app_commands
from dotenv import load_dotenv
import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pytz

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# Timezone setup (IST)
tz = pytz.timezone("Asia/Kolkata")

# Set up Google Sheets client
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_JSON, scopes=scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open_by_key(SHEET_ID).sheet1

# Ensure headers exist
EXPECTED_HEADERS = ["Date", "Amount", "Item", "Category"]
def ensure_headers():
    current_headers = sheet.row_values(1)
    if current_headers != EXPECTED_HEADERS:
        sheet.insert_row(EXPECTED_HEADERS, 1)

ensure_headers()

# Discord bot setup
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")

def get_expense_data():
    """Fetch all expense data from the sheet"""
    return sheet.get_all_records()

def filter_expenses_by_date(expenses, start_date, end_date=None):
    """Filter expenses between start_date and end_date (inclusive)"""
    filtered = []
    for expense in expenses:
        try:
            expense_date = datetime.strptime(expense['Date'], "%Y-%m-%d").date()
            if end_date:
                if start_date <= expense_date <= end_date:
                    filtered.append(expense)
            else:
                if expense_date == start_date:
                    filtered.append(expense)
        except Exception:
            continue  # Skip bad rows
    return filtered

def generate_summary(expenses):
    """Generate a summary of expenses"""
    if not expenses:
        return "No expenses found", 0
    
    total = sum(float(expense['Amount']) for expense in expenses)
    categories = {}

    for expense in expenses:
        category = expense['Category']
        amount = float(expense['Amount'])
        categories[category] = categories.get(category, 0) + amount

    sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)

    summary_lines = [
        f"**Total:** ₹{total:.2f}",
        "",
        "**By Category:**"
    ]
    for category, amount in sorted_categories:
        percentage = (amount / total) * 100
        summary_lines.append(f"- {category}: ₹{amount:.2f} ({percentage:.1f}%)")

    return "\n".join(summary_lines), total

@tree.command(name="ex", description="Log an expense (amount item category)")
@app_commands.describe(
    amount="Expense amount (e.g., 150)",
    item="What you spent on (e.g., coffee)",
    category="Category (e.g., food, transport)"
)
async def log_expense(interaction: discord.Interaction, amount: float, item: str, category: str):
    try:
        now = datetime.now(tz)
        current_date = now.strftime("%Y-%m-%d")
        sheet.append_row([current_date, str(amount), item, category])
        await interaction.response.send_message(
            f"✅ Logged: ₹{amount} on *{item}* under *{category}*",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Failed to log expense: {e}",
            ephemeral=True
        )

@tree.command(name="summary", description="Get expense summary for today")
async def summary_today(interaction: discord.Interaction):
    try:
        today = datetime.now(tz).date()
        expenses = get_expense_data()
        today_expenses = filter_expenses_by_date(expenses, today)
        summary, total = generate_summary(today_expenses)

        embed = discord.Embed(
            title=f"📊 Today's Expense Summary ({today.strftime('%b %d, %Y')})",
            description=summary,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Total Expenses: ₹{total:.2f}")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Failed to generate summary: {e}",
            ephemeral=True
        )

@tree.command(name="summary_week", description="Get expense summary for this week")
async def summary_week(interaction: discord.Interaction):
    try:
        today = datetime.now(tz).date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        expenses = get_expense_data()
        week_expenses = filter_expenses_by_date(expenses, start_of_week, end_of_week)
        summary, total = generate_summary(week_expenses)

        embed = discord.Embed(
            title=f"📊 Weekly Expense Summary ({start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')})",
            description=summary,
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Total Expenses: ₹{total:.2f}")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Failed to generate summary: {e}",
            ephemeral=True
        )

@tree.command(name="summary_month", description="Get expense summary for this month")
async def summary_month(interaction: discord.Interaction):
    try:
        today = datetime.now(tz).date()
        start_of_month = today.replace(day=1)
        end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        expenses = get_expense_data()
        month_expenses = filter_expenses_by_date(expenses, start_of_month, end_of_month)
        summary, total = generate_summary(month_expenses)

        embed = discord.Embed(
            title=f"📊 Monthly Expense Summary ({start_of_month.strftime('%B %Y')})",
            description=summary,
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Total Expenses: ₹{total:.2f}")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Failed to generate summary: {e}",
            ephemeral=True
        )

bot.run(TOKEN)
