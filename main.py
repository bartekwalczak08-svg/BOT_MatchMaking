import json
import os
import random
import string
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands

from config import COMMAND_PREFIX, DATA_DIR
from data_utils import load_json, save_json, ensure_data_dir

# Ensure data directory exists
ensure_data_dir()

TOKEN_FILE = "token.txt"

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
    try:
        synced = await bot.tree.sync()
        print(f"[BOT] Synced {len(synced)} commands")
    except Exception as e:
        print(f"[ERROR] Failed to sync commands: {e}")


# ===================== QUEUE =====================

@bot.tree.command(name='join_queue', description='Dołącz do kolejki na grę')
async def join_queue(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild.id)

    queues = load_json(QUEUES_FILE)
    players = load_json(PLAYERS_FILE)

    if user_id in queues.get(guild_id, []):
        await interaction.response.send_message("Już jesteś w kolejce!")
        return

    queues.setdefault(guild_id, []).append(user_id)

    players.setdefault(user_id, {})
    players[user_id]['nickname'] = str(interaction.user)
    players[user_id].setdefault('elo', 1000)
    players[user_id]['joined_at'] = datetime.now().isoformat()

    save_json(QUEUES_FILE, queues)
    save_json(PLAYERS_FILE, players)

    await interaction.response.send_message(f"Dołączyłeś do kolejki! ({len(queues[guild_id])} graczy)")


@bot.tree.command(name='leave_queue', description='Opuść kolejkę')
async def leave_queue(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild.id)

    queues = load_json(QUEUES_FILE)

    if guild_id in queues and user_id in queues[guild_id]:
        queues[guild_id].remove(user_id)

        if not queues[guild_id]:
            del queues[guild_id]

        save_json(QUEUES_FILE, queues)
        await interaction.response.send_message("Wyszedłeś z kolejki.")
    else:
        await interaction.response.send_message("Nie jesteś w kolejce.")


@bot.tree.command(name='queue', description='Pokaż aktualną kolejkę')
async def show_queue(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)

    queues = load_json(QUEUES_FILE)
    players = load_json(PLAYERS_FILE)

    guild_queue = queues.get(guild_id, [])

    if not guild_queue:
        await interaction.response.send_message("Kolejka jest pusta.")
        return

    msg = "**Kolejka:**\n"
    for i, uid in enumerate(guild_queue, 1):
        name = players.get(uid, {}).get('nickname', uid)
        msg += f"{i}. {name}\n"

    await interaction.response.send_message(msg)


# ===================== MATCHES =====================

@bot.tree.command(name='start_match', description='Utwórz nowy mecz')
async def start_match(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)

    queues = load_json(QUEUES_FILE)
    players = load_json(PLAYERS_FILE)
    matches = load_json(MATCHES_FILE)

    if guild_id not in queues or len(queues[guild_id]) < 2:
        await interaction.response.send_message("Za mało graczy (min. 2).")
        return

    selected = queues[guild_id][:2]
    queues[guild_id] = queues[guild_id][2:]

    if not queues[guild_id]:
        del queues[guild_id]

    match_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    matches[match_id] = {
        'guild_id': guild_id,
        'players': selected,
        'started_at': datetime.now().isoformat()
    }

    save_json(QUEUES_FILE, queues)
    save_json(MATCHES_FILE, matches)

    names = [players.get(p, {}).get('nickname', p) for p in selected]

    await interaction.response.send_message(f"🔥 Mecz start!\nID: {match_id}\nGracze: {', '.join(names)}")


@bot.tree.command(name='matches', description='Pokaż aktywne mecze')
async def list_matches(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)

    matches = load_json(MATCHES_FILE)
    players = load_json(PLAYERS_FILE)

    guild_matches = [(m_id, m) for m_id, m in matches.items() if m.get('guild_id') == guild_id]

    if not guild_matches:
        await interaction.response.send_message("Brak meczów.")
        return

    msg = "**Aktywne mecze:**\n"

    for m_id, m in guild_matches[-5:]:
        names = [players.get(p, {}).get('nickname', p) for p in m['players']]
        msg += f"ID: {m_id} - {', '.join(names)}\n"

    await interaction.response.send_message(msg)


# ===================== LEADERBOARD =====================

@bot.tree.command(name='leaderboard', description='Pokaż ranking graczy')
async def leaderboard(interaction: discord.Interaction, page: int = 1):
    players = load_json(PLAYERS_FILE)

    sorted_p = sorted(players.items(), key=lambda x: x[1].get("elo", 1000), reverse=True)

    per_page = 10
    total_pages = max(1, (len(sorted_p) + per_page - 1) // per_page)

    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_data = sorted_p[start:end]

    msg = f"🏆 Leaderboard — strona {page}/{total_pages}\n\n"

    for i, (pid, p) in enumerate(page_data, start=start + 1):
        name = p.get('nickname', pid)
        elo = p.get('elo', 1000)
        msg += f"{i}. {name} — {elo} ELO\n"

    class LBView(discord.ui.View):
        def __init__(self, user_id):
            super().__init__(timeout=120)
            self.user_id = user_id

        @discord.ui.button(label="◀", style=discord.ButtonStyle.blurple)
        async def prev(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != self.user_id:
                await button_interaction.response.send_message("Nie twoje.", ephemeral=True)
                return
            await button_interaction.response.defer()
            await button_interaction.message.delete()
            await leaderboard(button_interaction, page - 1)

        @discord.ui.button(label="▶", style=discord.ButtonStyle.blurple)
        async def next(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != self.user_id:
                await button_interaction.response.send_message("Nie twoje.", ephemeral=True)
                return
            await button_interaction.response.defer()
            await button_interaction.message.delete()
            await leaderboard(button_interaction, page + 1)

    view = LBView(interaction.user.id) if total_pages > 1 else None
    await interaction.response.send_message(msg, view=view)


# ===================== START =====================

def get_token():
    token = os.environ.get("DISCORD_TOKEN")

    if token:
        print("[BOT] Token z env")
        return token

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            print("[BOT] Token z pliku")
            return f.read().strip()

    return None


if __name__ == "__main__":
    print("[BOT] Start...")

    token = get_token()

    if not token:
        print("[ERROR] Brak tokena")
        exit(1)

    bot.run(token)