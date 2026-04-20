import json
import os
import random
import string
from datetime import datetime

import discord
from discord.ext import commands

from config import COMMAND_PREFIX, BOT_TOKEN_FILE, DATA_DIR
from utils.data import load_json, save_json

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

PLAYERS_FILE = "players.json"
QUEUES_FILE = "queues.json"
MATCHES_FILE = "matches.json"

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=INTENTS)

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in!')

@bot.command(name='join_queue')
async def join_queue(ctx):
    user_id = str(ctx.author.id)
    queues = load_json(QUEUES_FILE)
    players = load_json(PLAYERS_FILE)
    
    if user_id in queues.get(ctx.guild.id, []):
        await ctx.send("Jesteś już w kolejce!")
        return
    
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []
    
    queues[ctx.guild.id].append(user_id)
    players[user_id] = players.get(user_id, {})
    players[user_id]['name'] = str(ctx.author)
    players[user_id]['joined_at'] = datetime.now().isoformat()
    
    save_json(QUEUES_FILE, queues)
    save_json(PLAYERS_FILE, players)
    
    await ctx.send(f"Dołączono do kolejki! Aktualna kolejka: {len(queues[ctx.guild.id])} graczy.")

@bot.command(name='leave_queue')
async def leave_queue(ctx):
    user_id = str(ctx.author.id)
    queues = load_json(QUEUES_FILE)
    
    if ctx.guild.id in queues and user_id in queues[ctx.guild.id]:
        queues[ctx.guild.id].remove(user_id)
        if not queues[ctx.guild.id]:
            del queues[ctx.guild.id]
        save_json(QUEUES_FILE, queues)
        await ctx.send("Opuszczono kolejkę.")
    else:
        await ctx.send("Nie jesteś w kolejce!")

@bot.command(name='queue')
async def show_queue(ctx):
    queues = load_json(QUEUES_FILE)
    guild_queues = queues.get(ctx.guild.id, [])
    if not guild_queues:
        await ctx.send("Kolejka jest pusta.")
        return
    
    players = load_json(PLAYERS_FILE)
    queue_list = [players.get(uid, {}).get('name', uid) for uid in guild_queues]
    await ctx.send(f"Kolejka ({len(queue_list)}): {' -> '.join(queue_list)}")

@bot.command(name='start_match')
async def start_match(ctx):
    queues = load_json(QUEUES_FILE)
    guild_id = ctx.guild.id
    if guild_id not in queues or len(queues[guild_id]) < 2:
        await ctx.send("Za mało graczy w kolejce! Potrzeba min. 2.")
        return
    
    guild_queue = queues[guild_id][:2]  # Take first 2 for match
    queues[guild_id] = queues[guild_id][2:]  # Remove them
    if not queues[guild_id]:
        del queues[guild_id]
    
    players = load_json(PLAYERS_FILE)
    match_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    matches = load_json(MATCHES_FILE)
    matches[match_id] = {
        'guild_id': guild_id,
        'players': [players.get(p, {}).get('name', p) for p in guild_queue],
        'started_at': datetime.now().isoformat()
    }
    
    save_json(QUEUES_FILE, queues)
    save_json(MATCHES_FILE, matches)
    
    await ctx.send(f"Nowa gra! ID: {match_id}\nGracze: {', '.join(matches[match_id]['players'])}")

@bot.command(name='matches')
async def list_matches(ctx):
    matches = load_json(MATCHES_FILE)
    if not matches:
        await ctx.send("Brak gier.")
        return
    
    guild_matches = [m for m_id, m in matches.items() if m.get('guild_id') == ctx.guild.id]
    if not guild_matches:
        await ctx.send("Brak gier na tym serwerze.")
        return
    
    msg = "Aktywne gry:\n"
    for m in guild_matches[-5:]:  # Last 5
        msg += f"ID: {list(matches.keys())[list(matches.values()).index(m)]} - {', '.join(m['players'])}\n"
    await ctx.send(msg)

if __name__ == "__main__":
    if not os.path.exists(BOT_TOKEN_FILE):
        print(f"Create {BOT_TOKEN_FILE} with your bot token!")
        exit(1)
    
    with open(BOT_TOKEN_FILE, 'r') as f:
        token = f.read().strip()
    
    bot.run(token)
