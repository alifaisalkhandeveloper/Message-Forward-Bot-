import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext

# Replace 'YOUR_TOKEN' with the token you received from BotFather
TOKEN = '7788779108:AAHsoPD5U4i7OxvpL-St0KvIMNZIv2Uv28E'

# Admin's user ID (replace with actual admin user ID)
ADMIN_USER_ID = '6966950771'

# File to store user IDs
USER_FILE = 'users.txt'
BLOCKED_FILE = 'blocked_users.txt'

def load_users():
    """Load the user IDs from the users.txt file."""
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as f:
            users = f.read().splitlines()
        return set(users)
    return set()

def save_user(user_id):
    """Save a new user ID to the users.txt file."""
    with open(USER_FILE, 'a') as f:
        f.write(f"{user_id}\n")

def load_blocked_users():
    """Load the blocked users and their unblock time."""
    blocked_users = {}
    if os.path.exists(BLOCKED_FILE):
        with open(BLOCKED_FILE, 'r') as f:
            for line in f:
                user_id, unblock_time = line.strip().split(',')
                blocked_users[user_id] = datetime.fromisoformat(unblock_time)
    return blocked_users

def save_blocked_user(user_id, unblock_time):
    """Save a blocked user and their unblock time."""
    with open(BLOCKED_FILE, 'a') as f:
        f.write(f"{user_id},{unblock_time.isoformat()}\n")

def start_buttons():
    """Create inline buttons visible to all users."""
    keyboard = [
        [InlineKeyboardButton("Forward Message to Admin", callback_data='forward')],
        [InlineKeyboardButton("View Users", callback_data='users')],
        [InlineKeyboardButton("Block User", callback_data='block')],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: CallbackContext):
    """Handles the /start command."""
    user_id = str(update.message.chat_id)

    # Check if user is blocked
    blocked_users = load_blocked_users()
    if user_id in blocked_users:
        unblock_time = blocked_users[user_id]
        if datetime.now() < unblock_time:
            await update.message.reply_text(f"You are blocked until {unblock_time}.")
            return

    # Save the user ID to the file if not already saved
    if user_id not in load_users():
        save_user(user_id)

    # Send inline buttons to all users
    await update.message.reply_text(
        "Hello! Please message here , and your message will be delivered to admin!",
        reply_markup=start_buttons()
    )

async def forward_to_admin(update: Update, context: CallbackContext):
    """Forward user messages to the admin, including username, user ID, and clickable chat ID."""
    user_message = update.message.text
    user = update.message.from_user
    username = user.username if user.username else "No username"
    user_id = user.id
    
    # Creating a clickable link for the user chat ID in Markdown format
    chat_id_link = f"[{user_id}](tg://user?id={user_id})"
    
    message = f"The user {username} (User ID: {user_id}) has sent you the message:\n\n{user_message}\n\n"
    message += f"Click here to copy their User ID: {chat_id_link}"
    
    # Forward the message to the admin
    await context.bot.send_message(chat_id=ADMIN_USER_ID, text=message, parse_mode='Markdown')

async def forward_to_user(update: Update, context: CallbackContext):
    """Admin sends a message to a specific user."""
    if str(update.message.chat_id) == ADMIN_USER_ID:
        # Ensure the correct command format /forward <user_id> <message>
        if len(context.args) >= 2:
            user_id = context.args[0]
            message = ' '.join(context.args[1:])
            
            # Check if user_id is in the list
            if user_id in load_users():
                await context.bot.send_message(chat_id=user_id, text=message)
                await update.message.reply_text(f"Message forwarded to user {user_id}.")
            else:
                await update.message.reply_text("User ID not found.")
        else:
            await update.message.reply_text("Please provide a user ID and a message after the /forward command.")
    else:
        await update.message.reply_text("This command can only be run by the admin.")

async def users(update: Update, context: CallbackContext):
    """Admin views the list of users and their user IDs."""
    if str(update.message.chat_id) == ADMIN_USER_ID:
        users = load_users()
        user_count = len(users)
        user_list = "\n".join(users)
        await update.message.reply_text(f"Total users: {user_count}\n\nUser IDs:\n{user_list}")
    else:
        await update.message.reply_text("Only the admin can use this command.")

async def block_user(update: Update, context: CallbackContext):
    """Admin blocks a user for a certain duration."""
    if str(update.message.chat_id) == ADMIN_USER_ID:
        if len(context.args) == 2:
            user_id = context.args[0]
            try:
                duration = int(context.args[1])  # duration in minutes
                unblock_time = datetime.now() + timedelta(minutes=duration)

                # Block the user
                save_blocked_user(user_id, unblock_time)
                await context.bot.send_message(chat_id=user_id, text=f"You have been blocked from the bot until {unblock_time}.")
                await update.message.reply_text(f"User {user_id} has been blocked until {unblock_time}.")
            except ValueError:
                await update.message.reply_text("Invalid duration. Please provide a valid number of minutes.")
        else:
            await update.message.reply_text("Please provide a user ID and duration in minutes.")
    else:
        await update.message.reply_text("Only the admin can use this command.")

async def broadcast(update: Update, context: CallbackContext):
    """Admin can broadcast a message to all users."""
    if str(update.message.chat_id) == ADMIN_USER_ID:
        if context.args:
            message = ' '.join(context.args)
            users = load_users()
            for user_id in users:
                try:
                    await context.bot.send_message(chat_id=user_id, text=message)
                except Exception as e:
                    print(f"Failed to send message to {user_id}: {e}")
            await update.message.reply_text(f"Message broadcasted to {len(users)} users.")
        else:
            await update.message.reply_text("Please provide a message to broadcast.")
    else:
        await update.message.reply_text("Only the admin can use this command.")

async def handle_restricted_commands(update: Update, context: CallbackContext):
    """Handle cases where non-admins try to run restricted commands."""
    user_id = str(update.message.chat_id)
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("Only the admin can run this command.")

async def button_handler(update: Update, context: CallbackContext):
    """Handle button presses and restrict non-admins from using the buttons."""
    query = update.callback_query
    data = query.data
    user_id = str(query.from_user.id)

    if user_id == ADMIN_USER_ID:
        # Admin can use the buttons
        if data == 'forward':
            await query.answer()
            await query.message.reply_text("Please send the message you want to forward to the admin.")
        elif data == 'users':
            await query.answer()
            await users(update, context)
        elif data == 'block':
            await query.answer()
            await query.message.reply_text("Please send the user ID and the block duration (in minutes) after the /block command.")
    else:
        # Non-admins cannot use the buttons
        await query.answer()
        await query.message.reply_text("You do not have permission to use this option.")

def main():
    """Sets up the bot and its handlers."""
    # Create the Application and pass the bot token
    application = Application.builder().token(TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('forward', forward_to_user))
    application.add_handler(CommandHandler('users', users))
    application.add_handler(CommandHandler('block', block_user))
    application.add_handler(CommandHandler('broadcast', broadcast))

    # Message handler to forward all user messages to the admin
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_admin))

    # Handle restricted commands for non-admins
    application.add_handler(MessageHandler(filters.COMMAND, handle_restricted_commands))

    # CallbackQueryHandler to handle button presses
    application.add_handler(CallbackQueryHandler(button_handler))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
