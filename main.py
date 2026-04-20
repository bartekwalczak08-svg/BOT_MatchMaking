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
        await ctx.send("You're already in the queue!")
        return
    
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []
    
    queues[ctx.guild.id].append(user_id)
    players[user_id] = players.get(user_id, {})
    players[user_id]['name'] = str(ctx.author)
    players[user_id]['joined_at'] = datetime.now().isoformat()
    
    save_json(QUEUES_FILE, queues)
    save_json(PLAYERS_FILE, players)
    
    await ctx.send(f"Joined the queue! Current queue: {len(queues[ctx.guild.id])} players.")

@bot.command(name='leave_queue')
async def leave_queue(ctx):
    user_id = str(ctx.author.id)
    queues = load_json(QUEUES_FILE)
    
    if ctx.guild.id in queues and user_id in queues[ctx.guild.id]:
        queues[ctx.guild.id].remove(user_id)
        if not queues[ctx.guild.id]:
            del queues[ctx.guild.id]
        save_json(QUEUES_FILE, queues)
        await ctx.send("Left the queue.")
    else:
        await ctx.send("You're not in the queue!")

@bot.command(name='queue')
async def show_queue(ctx):
    queues = load_json(QUEUES_FILE)
    guild_queues = queues.get(ctx.guild.id, [])
    if not guild_queues:
        await ctx.send("The queue is empty.")
        return
    
    players = load_json(PLAYERS_FILE)
    queue_list = [players.get(uid, {}).get('name', uid) for uid in guild_queues]
    await ctx.send(f"Queue ({len(queue_list)}): {' -> '.join(queue_list)}")

@bot.command(name='start_match')
async def start_match(ctx):
    queues = load_json(QUEUES_FILE)
    guild_id = ctx.guild.id
    if guild_id not in queues or len(queues[guild_id]) < 2:
        await ctx.send("Not enough players in the queue! Need at least 2.")
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
    
    await ctx.send(f"New match! ID: {match_id}\nPlayers: {', '.join(matches[match_id]['players'])}")

@bot.command(name='matches')
async def list_matches(ctx):
    matches = load_json(MATCHES_FILE)
    if not matches:
        await ctx.send("No matches.")
        return
    
    guild_matches = [m for m_id, m in matches.items() if m.get('guild_id') == ctx.guild.id]
    if not guild_matches:
        await ctx.send("No matches on this server.")
        return
    
    msg = "Active matches:\n"
    for m in guild_matches[-5:]:  # Last 5
        msg += f"ID: {list(matches.keys())[list(matches.values()).index(m)]} - {', '.join(m['players'])}\n"
    await ctx.send(msg)

@bot.command()
async def leaderboard(ctx: commands.Context, page: int = 1):
    players = load_json(PLAYERS_FILE)

    sorted_p = sorted(players.items(), key=lambda x: x[1].get("elo", 0), reverse=True)

    per_page = 10
    total_pages = (len(sorted_p) + per_page - 1) // per_page

    page = max(1, min(page, total_pages if total_pages > 0 else 1))

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_data = sorted_p[start_idx:end_idx]

    emoji = "🔽"
    msg = f"5v5 Leaderboard (Top {len(sorted_p)}) — Page {page}/{total_pages}:\n"

    for i, (pid, p) in enumerate(page_data, start=start_idx + 1):
        msg += f"{i}. {emoji} {p.get('nickname','?')} - {p.get('elo',0)} ELO\n"

    class LeaderboardView(discord.ui.View):
        def __init__(self, ctx_author, current_page, max_pages):
            super().__init__(timeout=300)
            self.ctx_author = ctx_author
            self.current_page = current_page
            self.max_pages = max_pages

            self.prev_button.disabled = current_page <= 1
            self.next_button.disabled = current_page >= max_pages

        @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.blurple)
        async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.ctx_author:
                await interaction.response.send_message("You can't use this button.", ephemeral=True)
                return
            await interaction.response.defer()
            await interaction.message.delete()
            await ctx.invoke(leaderboard, page=self.current_page - 1)

        @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.blurple)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.ctx_author:
                await interaction.response.send_message("You can't use this button.", ephemeral=True)
                return
            await interaction.response.defer()
            await interaction.message.delete()
            await ctx.invoke(leaderboard, page=self.current_page + 1)

    view = LeaderboardView(ctx.author.id, page, total_pages) if total_pages > 1 else None
    await ctx.send(msg, view=view)

if __name__ == "__main__":
    if not os.path.exists(BOT_TOKEN_FILE):
        print(f"Create {BOT_TOKEN_FILE} with your bot token!")
        exit(1)
    
    with open(BOT_TOKEN_FILE, 'r') as f:
        token = f.read().strip()
    
    bot.run(MTQ5NTg1ODA1MzI4MTQ4MDc1NA.GjWOnT.1dbi1bVc1CiC9JWA2Y8hZieS3YFXe0tjz9-L2U)
