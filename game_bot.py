import random
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Replace these with your actual credentials
API_ID = "25064357"
API_HASH = "cda9f1b3f9da4c0c93d1f5c23ccb19e2"
BOT_TOKEN = "7329929698:AAGD5Ccwm0qExCq9_6GVHDp2E7iidLH-McU"
MONGO_URI = "mongodb+srv://tanjiro1564:tanjiro1564@cluster0.pp5yz4e.mongodb.net/?retryWrites=true&w=majority"

# Owner credentials
OWNER_ID = 1886390680  # Replace with the actual owner ID
OWNER_USERNAME = "sung_jinwo4"  # Replace with the actual owner username

# Initialize the Pyrogram Client
app = Client("game_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize the MongoDB client
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["game_bot"]
users_collection = db["users"]

# In-memory storage for ongoing games, user activity, and message tracking
ongoing_ttt_games = {}
active_users = set()
game_messages = {}
truth_dare_messages = {}
ongoing_chess_games = {}

# Lists of random truth questions and dare tasks
truth_questions = [
    "What is your biggest fear?", "Have you ever lied to a friend?", "What's the most embarrassing thing you have ever done?", 
    "What is a secret you've never told anyone?", "Have you ever cheated in an exam?", "Who is your secret crush?",
    "What's the most illegal thing you've done?", "What's the most childish thing you still do?", 
    "Have you ever stolen anything?", "What is the meanest thing you've ever said to someone?",
    # Add more truth questions up to 200
] * 20  # Duplicated to reach 200 questions for this example

dare_tasks = [
    "Do 10 pushups", "Sing a song loudly", "Dance for 1 minute without music", "Imitate a celebrity",
    "Do a funny face for 30 seconds", "Call someone and pretend it's their birthday", 
    "Pretend to be a cat for 2 minutes", "Speak in a foreign accent for the next 2 rounds",
    "Send a funny selfie to a group", "Eat a spoonful of ketchup", 
    # Add more dare tasks up to 200
] * 20  # Duplicated to reach 200 tasks for this example

# Function to get user score
def get_user_score(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user["score"] if user else 0

# Function to update user score
def update_user_score(user_id, username, points):
    users_collection.update_one({"user_id": user_id}, {"$set": {"username": username}, "$inc": {"score": points}}, upsert=True)

# Function to reset user score
def reset_user_score(user_id):
    users_collection.update_one({"user_id": user_id}, {"$set": {"score": 0}})

# Function to get leaderboard
def get_leaderboard():
    return list(users_collection.find().sort("score", -1).limit(10))

# Function to get leaderboard for a specific chat
def get_group_leaderboard(chat_id):
    return list(users_collection.find({"chat_id": chat_id}).sort("score", -1).limit(10))

# Command: /startht
@app.on_message(filters.command("startht") & filters.group)
async def start_ht(client, message):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Your Scorecard", callback_data="scorecard")],
            [InlineKeyboardButton("Leaderboard", callback_data="leaderboard")],
            [InlineKeyboardButton("My Master", url="http://t.me/sung_jinwo4")],
        ]
    )
    msg = await message.reply_text("Choose an option:", reply_markup=keyboard)
    game_messages[message.chat.id] = msg

# Command: /go
@app.on_message(filters.command("go") & filters.group)
async def start_head_tail_game(client, message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Check if user has already played
    if user_id in active_users:
        await message.reply_text("You have already played! Use /go again to start a new round.")
        return

    # Ensure user is in the database
    update_user_score(user_id, username, 0)

    # Mark user as active for this round
    active_users.add(user_id)

    # Send the game start message with options for Head or Tail
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Head", callback_data=f"choose_head_{user_id}")],
            [InlineKeyboardButton("Tail", callback_data=f"choose_tail_{user_id}")],
        ]
    )

    if message.chat.id in game_messages:
        # Edit the existing message
        await game_messages[message.chat.id].edit_text("Thanks for starting... Now choose:", reply_markup=keyboard)
    else:
        msg = await message.reply_text("Thanks for starting... Now choose:", reply_markup=keyboard)
        game_messages[message.chat.id] = msg

# Callback for choosing Head or Tail
@app.on_callback_query(filters.regex(r"^choose_"))
async def choose_option(client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[2])  # Extract user ID from callback data

    if callback_query.from_user.id != user_id:
        await callback_query.answer("This choice is not for you!", show_alert=True)
        return

    username = callback_query.from_user.username
    choice = callback_query.data.split("_")[1]  # 'head' or 'tail'
    
    # Randomly decide the outcome
    result = random.choice(["head", "tail"])

    # Determine if the user won
    if choice == result:
        update_user_score(user_id, username, 10)
        await callback_query.message.edit_text(f"Congratulations! It's {result}. You won 10 points!")
    else:
        await callback_query.message.edit_text(f"Sorry, it's {result}. Better luck next time!")

    # Remove user from active users set
    active_users.discard(user_id)
    await callback_query.answer()

# Callback for displaying user scorecard
@app.on_callback_query(filters.regex(r"^scorecard$"))
async def show_scorecard(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    score = get_user_score(user_id)
    await callback_query.message.edit_text(f"Your current score is: {score} points.")
    await callback_query.answer()

# Callback for displaying leaderboard
@app.on_callback_query(filters.regex(r"^leaderboard$"))
async def show_leaderboard(client, callback_query: CallbackQuery):
    leaderboard = get_leaderboard()
    response = "🏆 Leaderboard 🏆\n\n"
    for i, user in enumerate(leaderboard):
        response += f"{i + 1}. @{user['username']}: {user['score']} points\n"
    await callback_query.message.edit_text(response)
    await callback_query.answer()

# Command: /ttt - Start Tic Tac Toe game
@app.on_message(filters.command("ttt") & filters.group & filters.reply)
async def start_ttt_game(client, message):
    challenger = message.from_user.id
    opponent = message.reply_to_message.from_user.id

    if challenger == opponent:
        await message.reply_text("You cannot play with yourself. Challenge another member!")
        return

    if (challenger, opponent) in ongoing_ttt_games:
        await message.reply_text("A game is already ongoing between these members.")
        return

    # Initialize the Tic Tac Toe game state
    board = [" " for _ in range(9)]  # 3x3 board
    current_turn = challenger

    ongoing_ttt_games[(challenger, opponent)] = {
        "board": board,
        "turn": current_turn,
        "challenger": challenger,
        "opponent": opponent
    }

    # Show the initial board and prompt the first move
    await show_ttt_board(client, message.chat.id, challenger, opponent)

# Helper function to display the Tic Tac Toe board
async def show_ttt_board(client, chat_id, challenger, opponent):
    game = ongoing_ttt_games[(challenger, opponent)]
    board = game["board"]

    board_display = (
        f"{board[0]} | {board[1]} | {board[2]}\n"
        f"---------\n"
        f"{board[3]} | {board[4]} | {board[5]}\n"
        f"---------\n"
        f"{board[6]} | {board[7]} | {board[8]}"
    )

    turn_user = challenger if game["turn"] == challenger else opponent
    await client.send_message(chat_id, f"Tic Tac Toe Game:\n\n{board_display}\n\nIt's @{turn_user}'s turn!")

# Command: /rajapelerani - Start Chess Game
@app.on_message(filters.command("rajapelerani") & filters.group & filters.reply)
async def start_chess_game(client, message):
    challenger = message.from_user
    opponent = message.reply_to_message.from_user

    if challenger.id == opponent.id:
        await message.reply_text("You cannot play with yourself. Challenge another member!")
        return

    if (challenger.id, opponent.id) in ongoing_chess_games or (opponent.id, challenger.id) in ongoing_chess_games:
        await message.reply_text("A game is already ongoing between these members.")
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Accept", callback_data=f"accept_chess_{challenger.id}_{opponent.id}"),
          InlineKeyboardButton("Decline", callback_data=f"decline_chess_{challenger.id}_{opponent.id}")]]
    )
    await message.reply_text(f"{opponent.mention}, {challenger.mention} has challenged you to a game of chess!", reply_markup=keyboard)

# Callback for accepting or declining chess game
@app.on_callback_query(filters.regex(r"^(accept|decline)_chess_\d+_\d+$"))
async def chess_game_response(client, callback_query: CallbackQuery):
    action, challenger_id, opponent_id = callback_query.data.split("_")
    challenger_id = int(challenger_id)
    opponent_id = int(opponent_id)

    if action == "decline":
        await callback_query.message.edit_text("The chess challenge was declined.")
        await callback_query.answer()
        return

    if callback_query.from_user.id != opponent_id:
        await callback_query.answer("This challenge isn't for you!", show_alert=True)
        return

    if action == "accept":
        # Randomly assign colors
        if random.choice([True, False]):
            white, black = challenger_id, opponent_id
        else:
            white, black = opponent_id, challenger_id

        ongoing_chess_games[(challenger_id, opponent_id)] = {
            "white": white,
            "black": black,
            "turn": white,
            "board": initialize_chess_board()
        }

        await callback_query.message.edit_text(f"Chess game started!\n\nWhite: @{white}\nBlack: @{black}\n\n@{white}, it's your turn to move.")
        await callback_query.answer()

# Helper function to initialize chess board
def initialize_chess_board():
    # Simplified representation, adjust as needed
    board = [
        ["r", "n", "b", "q", "k", "b", "n", "r"],
        ["p", "p", "p", "p", "p", "p", "p", "p"],
        [" ", " ", " ", " ", " ", " ", " ", " "],
        [" ", " ", " ", " ", " ", " ", " ", " "],
        [" ", " ", " ", " ", " ", " ", " ", " "],
        [" ", " ", " ", " ", " ", " ", " ", " "],
        ["P", "P", "P", "P", "P", "P", "P", "P"],
        ["R", "N", "B", "Q", "K", "B", "N", "R"]
    ]
    return board

# Command: /chuplawde - Reset user score
@app.on_message(filters.command("chuplawde") & filters.user(OWNER_ID))
async def reset_score(client, message):
    if not message.reply_to_message:
        await message.reply_text("Reply to the user whose score you want to reset.")
        return

    target_user_id = message.reply_to_message.from_user.id
    reset_user_score(target_user_id)
    await message.reply_text("User's score has been reset to 0.")

# Command: /ldbd - Show local leaderboard
@app.on_message(filters.command("ldbd") & filters.group)
async def show_group_leaderboard(client, message):
    chat_id = message.chat.id
    leaderboard = get_group_leaderboard(chat_id)
    response = "🏆 Group Leaderboard 🏆\n\n"
    for i, user in enumerate(leaderboard):
        response += f"{i + 1}. @{user['username']}: {user['score']} points\n"
    await message.reply_text(response)

# Run the bot
app.run()

