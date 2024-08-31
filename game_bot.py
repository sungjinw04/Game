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

# Initialize the Pyrogram Client
app = Client("game_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize the MongoDB client
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["game_bot"]
users_collection = db["users"]

# In-memory storage for ongoing games and user activity
ongoing_ttt_games = {}
active_users = set()

# Function to get user score
def get_user_score(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user["score"] if user else 0

# Function to update user score
def update_user_score(user_id, username, points):
    users_collection.update_one({"user_id": user_id}, {"$set": {"username": username}, "$inc": {"score": points}}, upsert=True)

# Function to get leaderboard
def get_leaderboard():
    return list(users_collection.find().sort("score", -1).limit(10))

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
    await message.reply_text("Choose an option:", reply_markup=keyboard)

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
    await message.reply_text("Thanks for starting... Now choose:", reply_markup=keyboard)

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
        await callback_query.message.reply_text(f"Congratulations! It's {result}. You won 10 points!")
    else:
        await callback_query.message.reply_text(f"Sorry, it's {result}. Better luck next time!")

    # Remove user from active users set
    active_users.discard(user_id)
    await callback_query.answer()

# Callback for displaying user scorecard
@app.on_callback_query(filters.regex(r"^scorecard$"))
async def show_scorecard(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    score = get_user_score(user_id)
    await callback_query.message.reply_text(f"Your current score is: {score} points.")
    await callback_query.answer()

# Callback for displaying leaderboard
@app.on_callback_query(filters.regex(r"^leaderboard$"))
async def show_leaderboard(client, callback_query: CallbackQuery):
    leaderboard = get_leaderboard()
    response = "🏆 Leaderboard 🏆\n\n"
    for i, user in enumerate(leaderboard):
        response += f"{i + 1}. @{user['username']}: {user['score']} points\n"
    await callback_query.message.reply_text(response)
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

    # Show the game board
    await show_ttt_board(client, message.chat.id, board, challenger, opponent)

async def show_ttt_board(client, chat_id, board, challenger, opponent):
    # Display Tic Tac Toe board with inline buttons
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(board[i] if board[i] != " " else str(i + 1), callback_data=f"ttt_move_{i}_{challenger}_{opponent}")
            for i in range(j, j + 3)
        ] for j in range(0, 9, 3)]
    )
    await client.send_message(chat_id, "Tic Tac Toe Game! Use the buttons below to make a move.", reply_markup=keyboard)

# Callback for Tic Tac Toe moves
@app.on_callback_query(filters.regex(r"^ttt_move_"))
async def ttt_move(client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    move_index = int(data[2])
    challenger = int(data[3])
    opponent = int(data[4])
    game_key = (challenger, opponent)

    # Check if there is an ongoing game
    if game_key not in ongoing_ttt_games:
        await callback_query.answer("No ongoing game found.", show_alert=True)
        return

    game = ongoing_ttt_games[game_key]

    if callback_query.from_user.id != game["turn"]:
        await callback_query.answer("It's not your turn!", show_alert=True)
        return

    # Make a move
    if game["board"][move_index] == " ":
        game["board"][move_index] = "X" if game["turn"] == challenger else "O"
        game["turn"] = opponent if game["turn"] == challenger else challenger
    else:
        await callback_query.answer("Invalid move. Try another cell.", show_alert=True)
        return

    # Check for a winner or draw
    winner = check_ttt_winner(game["board"])
    if winner:
        update_user_score(winner, callback_query.from_user.username, 30)
        await callback_query.message.reply_text(f"Game Over! @{callback_query.from_user.username} won and received 30 points!")
        del ongoing_ttt_games[game_key]
    elif " " not in game["board"]:
        # Game is a draw
        update_user_score(challenger, callback_query.from_user.username, 7)
        update_user_score(opponent, callback_query.from_user.username, 7)
        await callback_query.message.reply_text("Game Over! It's a draw. Both players receive 7 points each.")
        del ongoing_ttt_games[game_key]
    else:
        # Continue the game
        await show_ttt_board(client, callback_query.message.chat.id, game["board"], challenger, opponent)

    await callback_query.answer()

def check_ttt_winner(board):
    # Check all winning combinations
    win_combinations = [(0, 1, 2), (3, 4, 5), (6, 7, 8), 
                        (0, 3, 6), (1, 4, 7), (2, 5, 8),
                        (0, 4, 8), (2, 4, 6)]
    for a, b, c in win_combinations:
        if board[a] == board[b] == board[c] and board[a] != " ":
            return True
    return False

# Run the bot
if __name__ == "__main__":
    print("Bot is starting...")
    app.run()

