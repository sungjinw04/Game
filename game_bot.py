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
    if chat_id in game_messages:
        await game_messages[chat_id].edit_text("Tic Tac Toe Game! Use the buttons below to make a move.", reply_markup=keyboard)
    else:
        msg = await client.send_message(chat_id, "Tic Tac Toe Game! Use the buttons below to make a move.", reply_markup=keyboard)
        game_messages[chat_id] = msg

# Callback for Tic Tac Toe moves
@app.on_callback_query(filters.regex(r"^ttt_move_"))
async def ttt_move(client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    move_position = int(data[2])
    challenger = int(data[3])
    opponent = int(data[4])

    if (challenger, opponent) not in ongoing_ttt_games:
        await callback_query.answer("Game not found!", show_alert=True)
        return

    game = ongoing_ttt_games[(challenger, opponent)]
    board = game["board"]
    current_turn = game["turn"]

    if callback_query.from_user.id != current_turn:
        await callback_query.answer("It's not your turn!", show_alert=True)
        return

    if board[move_position] != " ":
        await callback_query.answer("This position is already taken!", show_alert=True)
        return

    # Update board
    board[move_position] = "X" if current_turn == challenger else "O"

    # Check for win or draw
    if check_win(board):
        winner = callback_query.from_user.id
        update_user_score(winner, callback_query.from_user.username, 15)
        await callback_query.message.edit_text(f"Congratulations! {callback_query.from_user.mention} has won the game!")
        del ongoing_ttt_games[(challenger, opponent)]
    elif " " not in board:
        await callback_query.message.edit_text("It's a draw!")
        del ongoing_ttt_games[(challenger, opponent)]
    else:
        # Switch turns
        game["turn"] = opponent if current_turn == challenger else challenger
        await show_ttt_board(client, callback_query.message.chat.id, board, challenger, opponent)

    await callback_query.answer()

def check_win(board):
    win_conditions = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
    for condition in win_conditions:
        if board[condition[0]] == board[condition[1]] == board[condition[2]] != " ":
            return True
    return False

# Command: /chess - Start a Chess game
@app.on_message(filters.command("chess") & filters.group & filters.reply)
async def start_chess_game(client, message):
    challenger = message.from_user.id
    opponent = message.reply_to_message.from_user.id

    if challenger == opponent:
        await message.reply_text("You cannot play with yourself. Challenge another member!")
        return

    if (challenger, opponent) in ongoing_chess_games:
        await message.reply_text("A game is already ongoing between these members.")
        return

    # Initialize the Chess game state
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
    current_turn = challenger

    ongoing_chess_games[(challenger, opponent)] = {
        "board": board,
        "turn": current_turn,
        "challenger": challenger,
        "opponent": opponent
    }

    # Show the Chess board
    await show_chess_board(client, message.chat.id, board, challenger, opponent)

async def show_chess_board(client, chat_id, board, challenger, opponent):
    pieces = {
        "r": "♜", "n": "♞", "b": "♝", "q": "♛", "k": "♚", "p": "♟",
        "R": "♖", "N": "♘", "B": "♗", "Q": "♕", "K": "♔", "P": "♙",
        " ": "⬜"
    }

    # Create the chess board with inline buttons
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(pieces[board[i][j]], callback_data=f"chess_move_{i}_{j}_{challenger}_{opponent}")
                for j in range(8)
            ]
            for i in range(8)
        ]
    )

    if chat_id in game_messages:
        await game_messages[chat_id].edit_text("Chess Game! Use the buttons below to make a move.", reply_markup=keyboard)
    else:
        msg = await client.send_message(chat_id, "Chess Game! Use the buttons below to make a move.", reply_markup=keyboard)
        game_messages[chat_id] = msg

# Callback for Chess moves
@app.on_callback_query(filters.regex(r"^chess_move_"))
async def chess_move(client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    row, col = int(data[2]), int(data[3])
    challenger = int(data[4])
    opponent = int(data[5])

    if (challenger, opponent) not in ongoing_chess_games:
        await callback_query.answer("Game not found!", show_alert=True)
        return

    game = ongoing_chess_games[(challenger, opponent)]
    board = game["board"]
    current_turn = game["turn"]

    if callback_query.from_user.id != current_turn:
        await callback_query.answer("It's not your turn!", show_alert=True)
        return

    # Implement chess move logic (move validation, checkmate, etc.)

    # For simplicity, let's just update the piece to a dummy move
    # Update board (this is just a placeholder, real chess logic needed)
    board[row][col] = " "

    # Check for checkmate or draw (not implemented here)
    # if check_checkmate(board):
    #     winner = callback_query.from_user.id
    #     update_user_score(winner, callback_query.from_user.username, 30)
    #     await callback_query.message.edit_text(f"Congratulations! {callback_query.from_user.mention} has won the chess game!")
    #     del ongoing_chess_games[(challenger, opponent)]
    # elif check_draw(board):
    #     await callback_query.message.edit_text("It's a draw!")
    #     del ongoing_chess_games[(challenger, opponent)]
    # else:
    #     # Switch turns
    game["turn"] = opponent if current_turn == challenger else challenger
    await show_chess_board(client, callback_query.message.chat.id, board, challenger, opponent)

    await callback_query.answer()

# Command: /truth - Ask a random truth question
@app.on_message(filters.command("truth") & filters.group)
async def ask_truth(client, message):
    question = random.choice(truth_questions)
    msg = await message.reply_text(f"Truth: {question}")
    truth_dare_messages[message.chat.id] = msg

# Command: /dare - Give a random dare task
@app.on_message(filters.command("dare") & filters.group)
async def give_dare(client, message):
    task = random.choice(dare_tasks)
    msg = await message.reply_text(f"Dare: {task}")
    truth_dare_messages[message.chat.id] = msg

if __name__ == "__main__":
    print("Bot started...")
    app.run()

