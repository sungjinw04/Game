import random
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pymongo import MongoClient
from dotenv import load_dotenv
import asyncio
from english_words import english_words_lower_alpha_set


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
word_game_players = []
ongoing_word_game = None


def check_reply(msg):
    return (
        msg.from_user.id == player and
        msg.chat.id == chat_id and
        msg.text and
        len(msg.text) >= word_length and
        msg.text.lower().startswith(letter) and
        msg.text.lower() in english_words_lower_alpha_set
    )

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
async def handle_ttt_move(client, callback_query: CallbackQuery):
    data = callback_query.data.split("_")
    move = int(data[2])
    challenger = int(data[3])
    opponent = int(data[4])

    game = ongoing_ttt_games.get((challenger, opponent))

    if not game:
        await callback_query.answer("This game is no longer active.", show_alert=True)
        return

    user_id = callback_query.from_user.id

    if user_id != game["turn"]:
        await callback_query.answer("It's not your turn!", show_alert=True)
        return

    board = game["board"]

    if board[move] != " ":
        await callback_query.answer("Invalid move!", show_alert=True)
        return

    # Update the board with the player's move
    board[move] = "X" if user_id == challenger else "O"

    # Check for a winner or a draw
    winner = check_winner(board)
    if winner:
        winner_name = "Challenger" if winner == "X" else "Opponent"
        await callback_query.message.edit_text(f"Game over! {winner_name} wins!")
        del ongoing_ttt_games[(challenger, opponent)]
        return

    if " " not in board:
        await callback_query.message.edit_text("It's a draw!")
        del ongoing_ttt_games[(challenger, opponent)]
        return

    # Switch turns
    game["turn"] = opponent if user_id == challenger else challenger

    # Update the game board
    await show_ttt_board(client, callback_query.message.chat.id, board, challenger, opponent)

    await callback_query.answer()

# Function to check for a winner in Tic Tac Toe
def check_winner(board):
    # Define the winning combinations
    winning_combinations = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Rows
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Columns
        (0, 4, 8), (2, 4, 6)  # Diagonals
    ]

    for combo in winning_combinations:
        if board[combo[0]] == board[combo[1]] == board[combo[2]] != " ":
            return board[combo[0]]  # Return the winning symbol ('X' or 'O')

    return None

# Command: /chess - Start a chess game
@app.on_message(filters.command("chess") & filters.group & filters.reply)
async def start_chess_game(client, message):
    challenger = message.from_user.id
    opponent = message.reply_to_message.from_user.id

    if challenger == opponent:
        await message.reply_text("You cannot play with yourself. Challenge another member!")
        return

    if (challenger, opponent) in ongoing_chess_games:
        await message.reply_text("A chess game is already ongoing between these members.")
        return

    # Initialize the chess game state (using a simple dictionary for demo)
    chess_board = [" " for _ in range(64)]  # Simplified 8x8 board for demo
    current_turn = challenger

    ongoing_chess_games[(challenger, opponent)] = {
        "board": chess_board,
        "turn": current_turn,
        "challenger": challenger,
        "opponent": opponent
    }

    await message.reply_text("Chess game started! (This is a simplified demo version.)")

# Command: /stopchess - Stop an ongoing chess game
@app.on_message(filters.command("stopchess") & filters.group)
async def stop_chess_game(client, message):
    user_id = message.from_user.id
    found_game = None

    for game in ongoing_chess_games.keys():
        if user_id in game:
            found_game = game
            break

    if found_game:
        del ongoing_chess_games[found_game]
        await message.reply_text("The chess game has been stopped.")
    else:
        await message.reply_text("You are not in an ongoing chess game.")

# English word game implementation
@app.on_message(filters.command("russianpelo") & filters.group)
async def start_word_game(client, message):
    global word_game_players, ongoing_word_game

    if ongoing_word_game:
        await message.reply_text("A word game is already ongoing!")
        return

    word_game_players = []
    ongoing_word_game = True
    await message.reply_text("A new word game has started! Type /joinchudai to join. You have 1 minute to join.")

    await asyncio.sleep(60)  # Wait for players to join

    if not word_game_players:
        ongoing_word_game = False
        await message.reply_text("No players joined the game. Game cancelled.")
        return

    await message.reply_text("The game is starting now!")
    await start_next_round(client, message.chat.id, 3, 20)

@app.on_message(filters.command("joinchudai") & filters.group)
async def join_word_game(client, message):
    global word_game_players

    if not ongoing_word_game:
        await message.reply_text("There is no active game to join.")
        return

    if message.from_user.id in word_game_players:
        await message.reply_text("You have already joined the game!")
        return

    word_game_players.append(message.from_user.id)
    await message.reply_text(f"{message.from_user.mention} has joined the game!")

@app.on_message(filters.command("gangbang") & filters.group)
async def force_start_game(client, message):
    global ongoing_word_game

    # Check if the user is an admin
    try:
        chat_member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            await message.reply_text("Only admins can force start the game.")
            return
    except Exception as e:
        await message.reply_text("An error occurred while verifying admin status.")
        return

    if not word_game_players:
        await message.reply_text("No players have joined. Cannot start the game.")
        return

    if ongoing_word_game:
        await message.reply_text("A word game is already ongoing!")
        return

    ongoing_word_game = True
    await message.reply_text("The game is starting now!")
    await start_next_round(client, message.chat.id, 3, 20)

async def start_next_round(client, chat_id, word_length, time_limit):
    global word_game_players, ongoing_word_game

    player = random.choice(word_game_players)
    letter = random.choice("abcdefghijklmnopqrstuvwxyz")
    
    await client.send_message(chat_id, f"@{player}, your letter is '{letter}'. You have {time_limit} seconds to write a word with at least {word_length} letters.")
    
    def check_reply(msg):
        return (
            msg.from_user.id == player and
            msg.chat.id == chat_id and
            msg.text and
            len(msg.text) >= word_length and
            msg.text.lower().startswith(letter) and
            msg.text.lower() in english_words_lower_alpha_set  # Ensure word is valid
        )

    try:
        combined_filter = filters.text & filters.create(check_reply)
        response = await client.listen(filters=combined_filter, timeout=time_limit)
        
        if response:
            last_letter = response.text[-1].lower()
            await client.send_message(chat_id, f"Good job! The next word must start with '{last_letter}'.")
            
            # Update the letter for the next player
            letter = last_letter

            # Proceed to the next round with updated word length and time limit
            if len(word_game_players) > 1 and time_limit > 1:
                await start_next_round(client, chat_id, word_length + 1, time_limit - 1)
            else:
                await client.send_message(chat_id, "Game over! Congratulations to all participants!")
                ongoing_word_game = False

    except asyncio.TimeoutError:
        await client.send_message(chat_id, "Time's up! You failed to respond in time.")
        word_game_players.remove(player)
        if word_game_players:
            # Proceed to the next round without increasing word length or decreasing time
            await start_next_round(client, chat_id, word_length, time_limit)
        else:
            await client.send_message(chat_id, "Game over! No more players left.")
            ongoing_word_game = False

# Command: /help - Show all available commands
@app.on_message(filters.command("help") & filters.group)
async def show_help(client, message):
    help_text = """
**Available Commands:**
- `/startht` - Start the Head or Tail game
- `/go` - Play a round of Head or Tail
- `/ttt` - Start a Tic Tac Toe game
- `/chess` - Start a simplified chess game
- `/stopchess` - Stop an ongoing chess game
- `/russianpelo` - Start a new English word game
- `/joinchudai` - Join the ongoing English word game
- `/gangbang` - Force start the word game (admins only)
- `/help` - Show this help message
"""
    await message.reply_text(help_text, parse_mode="markdown")



if __name__ == "__main__":
    print("Bot started...")
    app.run()
