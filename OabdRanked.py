import os
import discord
import enum
import sqlite3
import asyncio
import random

MATCH_CATEGORY_NAME = "▬▬Ranked Bot▬▬"

SEASON_ADMINS = [
    333376788770062336,
    206068524890718218,
]

ALLOWED_CHANNEL_ID = 1500277677465272380

def is_queue_channel(interaction: discord.Interaction) -> bool:
    return interaction.channel.id == ALLOWED_CHANNEL_ID

def is_match_channel(interaction: discord.Interaction) -> bool:
    if interaction.channel.category is None:
        return False
    return interaction.channel.category.name == MATCH_CATEGORY_NAME

from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ─── ENUMS ───────────────────────────────────────────────────────────────────

class Region(enum.Enum):
    North_America = "NA"
    Europe = "EU"
    Asia = "AS"

class Ability(enum.Enum):
    SP_Soda = "SP Soda"; SPSO = "SPSO"; SPTW = "SPTW"; SPP = "SPP"
    SPOH = "SPOH"; Classic_SP = "Classic SP"; Classic_TW = "Classic TW"
    TW = "TW"; VTW = "VTW"; TWOH = "TWOH"; OSTW = "OSTW"; STW = "STW"
    NSTW = "NSTW"; TW_S = "TW:S"; Vampire = "Vampire"; Pillarman = "Pillarman"
    Kars = "Kars"; Stone_Free = "Stone Free"; Diver_Down = "Diver Down"
    WS = "WS"; C_MOON = "C-MOON"; MIH = "MIH"; CMIH = "CMIH"; CD = "CD"
    Classic_CD = "Classic CD"; The_Hand = "The Hand"; KQ = "KQ"; CKQ = "CKQ"
    KQBTD = "KQBTD"; CKQBTD = "CKQBTD"; KC = "KC"; CKC = "CKC"
    KCAU = "KCAU"; CKCAU = "CKCAU"; SAW = "SAW"; Spin = "Spin"
    Hamon = "Hamon"; TA1 = "TA1"; TA2 = "TA2"; TA3 = "TA3"; TA4 = "TA4"
    WR = "WR"; TWAU = "TWAU"; KQAU = "KQAU"; Sticky_Fingers = "Sticky Fingers"
    Mr_President = "Mr President"; PSC = "PSC"; WSU = "WSU"
    Steve_Platinum = "Steve Platinum"; OGER = "OGER"; GER = "GER"
    Anubis = "Anubis"; SC = "SC"; HG = "HG"; Chaka = "Chaka"; D13 = "D13"
    The_Emperor = "The Emperor"; Cream = "Cream"; GE = "GE"
    Purple_Haze = "Purple Haze"; Doppio_1arm = "Doppio 1 arm"
    Doppio_2arm = "Doppio 2 arm"; D4C = "D4C"; CD4C = "CD4C"
    Deimos = "Deimos"

class SetType(enum.Enum):
    Bo1 = "Best of 1"
    Bo3 = "Best of 3"
    Bo5 = "Best of 5"

# ─── DIVISION SYSTEM ─────────────────────────────────────────────────────────

DIVISIONS = ["F Team", "D Team", "C Team", "B Team", "A Team", "S Team"]
EX_TEAM_MAX = 10
MAX_LP_GAIN = 30

ex_team_roster = {}

REGION_PRIORITY = {
    "NA": ["NA", "EU", "AS"],
    "EU": ["EU", "NA", "AS"],
    "AS": ["AS", "EU", "NA"],
}

def elo_to_division(elo: int):
    index = min(elo // 100, len(DIVISIONS) - 1)
    lp = elo % 100
    return DIVISIONS[index], lp

def division_to_elo(division: str, lp: int = 0):
    index = DIVISIONS.index(division)
    return index * 100 + lp

def is_ex_team(user_id: int):
    return user_id in ex_team_roster

def get_ex_team_rank(user_id: int):
    sorted_ex = sorted(ex_team_roster.items(), key=lambda x: x[1], reverse=True)
    for i, (uid, pts) in enumerate(sorted_ex):
        if uid == user_id:
            return i + 1, pts
    return None, None

# ─── DATABASE ────────────────────────────────────────────────────────────────

conn = sqlite3.connect("ranked.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        elo INTEGER DEFAULT 0,
        placements_played INTEGER DEFAULT 0,
        placements_won INTEGER DEFAULT 0,
        ranked BOOLEAN DEFAULT 0,
        demotion_protection INTEGER DEFAULT 0
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        match_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player1_id INTEGER,
        player2_id INTEGER,
        channel_id INTEGER,
        winner_id INTEGER DEFAULT NULL,
        player1_reported INTEGER DEFAULT NULL,
        player2_reported INTEGER DEFAULT NULL,
        region TEXT,
        ability TEXT,
        set_type TEXT,
        created_at TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_stats (
        user_id INTEGER PRIMARY KEY,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS farming_cooldowns (
        user_id INTEGER,
        opponent_id INTEGER,
        count INTEGER DEFAULT 0,
        cooldown_until TEXT,
        PRIMARY KEY (user_id, opponent_id)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS ex_team (
        user_id INTEGER PRIMARY KEY,
        points INTEGER DEFAULT 0
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        display_name TEXT,
        bio TEXT DEFAULT '',
        joined_at TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS seasons (
        season_id INTEGER PRIMARY KEY AUTOINCREMENT,
        season_number INTEGER,
        started_at TEXT,
        ended_at TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS season_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        season_number INTEGER,
        final_elo INTEGER,
        final_division TEXT,
        final_lp INTEGER,
        wins INTEGER,
        losses INTEGER
    )
""")

try:
    cursor.execute("ALTER TABLE players ADD COLUMN season_number INTEGER DEFAULT 1")
    conn.commit()
except:
    pass

try:
    cursor.execute("ALTER TABLE players ADD COLUMN demotion_protection INTEGER DEFAULT 0")
    conn.commit()
except:
    pass

try:
    cursor.execute("ALTER TABLE profiles ADD COLUMN preferred_region TEXT DEFAULT NULL")
    cursor.execute("ALTER TABLE profiles ADD COLUMN preferred_ability TEXT DEFAULT NULL")
    conn.commit()
except:
    pass

try:
    cursor.execute("ALTER TABLE matches ADD COLUMN winner_id_final INTEGER DEFAULT NULL")
    cursor.execute("ALTER TABLE matches ADD COLUMN lp_change INTEGER DEFAULT 0")
    conn.commit()
except:
    pass

conn.commit()

def get_player(user_id: int):
    cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def create_player(user_id: int):
    cursor.execute("INSERT OR IGNORE INTO players (user_id) VALUES (?)", (user_id,))
    conn.commit()

def update_elo(user_id: int, new_elo: int):
    cursor.execute("UPDATE players SET elo = ? WHERE user_id = ?", (new_elo, user_id))
    conn.commit()

def get_demotion_protection(user_id: int):
    cursor.execute("SELECT demotion_protection FROM players WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def set_demotion_protection(user_id: int, value: int):
    cursor.execute("UPDATE players SET demotion_protection = ? WHERE user_id = ?", (value, user_id))
    conn.commit()

def get_stats(user_id: int):
    cursor.execute("SELECT * FROM player_stats WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def create_stats(user_id: int):
    cursor.execute("INSERT OR IGNORE INTO player_stats (user_id) VALUES (?)", (user_id,))
    conn.commit()

def add_win(user_id: int):
    create_stats(user_id)
    cursor.execute("UPDATE player_stats SET wins = wins + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def add_loss(user_id: int):
    create_stats(user_id)
    cursor.execute("UPDATE player_stats SET losses = losses + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def get_current_season():
    cursor.execute("SELECT season_number, started_at FROM seasons ORDER BY season_id DESC LIMIT 1")
    row = cursor.fetchone()
    return row if row else (1, "Unknown")

def record_season_history(user_id: int, season_number: int, elo: int, wins: int, losses: int):
    division, lp = elo_to_division(elo)
    cursor.execute("""
        INSERT INTO season_history (user_id, season_number, final_elo, final_division, final_lp, wins, losses)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, season_number, elo, division, lp, wins, losses))

def calculate_lp_change(winner_elo: int, loser_elo: int, winner_id: int = None):
    base = 20
    division_diff = (loser_elo // 100) - (winner_elo // 100)
    gain_bonus = max(0, division_diff * 5)
    gain = base + gain_bonus
    loss_bonus = max(0, -division_diff * 10)
    loss = base + loss_bonus
    if winner_id and (is_ex_team(winner_id) or winner_elo >= 500):
        gain = min(gain, MAX_LP_GAIN)
    return gain, loss

def load_ex_team():
    cursor.execute("SELECT user_id, points FROM ex_team")
    rows = cursor.fetchall()
    for user_id, points in rows:
        ex_team_roster[user_id] = points

def save_ex_team(user_id: int, points: int):
    cursor.execute("""
        INSERT INTO ex_team (user_id, points) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET points = ?
    """, (user_id, points, points))
    conn.commit()

def remove_ex_team(user_id: int):
    cursor.execute("DELETE FROM ex_team WHERE user_id = ?", (user_id,))
    conn.commit()
    ex_team_roster.pop(user_id, None)

def try_promote_to_ex_db(user_id: int, s_points: int):
    ex_team_roster[user_id] = s_points
    save_ex_team(user_id, s_points)
    if len(ex_team_roster) > EX_TEAM_MAX:
        lowest = min(ex_team_roster, key=ex_team_roster.get)
        remove_ex_team(lowest)
        return lowest
    return None

# ─── ANTI-FARMING ────────────────────────────────────────────────────────────

recent_opponents = {}

def load_cooldowns():
    cursor.execute("SELECT user_id, opponent_id, count, cooldown_until FROM farming_cooldowns")
    rows = cursor.fetchall()
    for user_id, opponent_id, count, cooldown_until in rows:
        if user_id not in recent_opponents:
            recent_opponents[user_id] = {}
        recent_opponents[user_id][opponent_id] = {
            "count": count,
            "cooldown_until": datetime.fromisoformat(cooldown_until)
        }

def save_cooldown(user_id: int, opponent_id: int, count: int, cooldown_until: datetime):
    cursor.execute("""
        INSERT INTO farming_cooldowns (user_id, opponent_id, count, cooldown_until)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, opponent_id) DO UPDATE SET count = ?, cooldown_until = ?
    """, (user_id, opponent_id, count, cooldown_until.isoformat(), count, cooldown_until.isoformat()))
    conn.commit()

def reset_cooldown_db(user_id: int, opponent_id: int):
    cursor.execute("""
        INSERT INTO farming_cooldowns (user_id, opponent_id, count, cooldown_until)
        VALUES (?, ?, 0, ?)
        ON CONFLICT(user_id, opponent_id) DO UPDATE SET count = 0, cooldown_until = ?
    """, (user_id, opponent_id, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
    conn.commit()

def get_cooldown_minutes(count: int):
    if count == 1:
        return 1
    if count == 2:
        return 3
    return None

def is_on_cooldown(user_id: int, opponent_id: int):
    now = datetime.utcnow()
    if user_id not in recent_opponents:
        return False
    if opponent_id not in recent_opponents[user_id]:
        return False
    entry = recent_opponents[user_id][opponent_id]
    if entry["count"] >= 3:
        return True
    if now < entry["cooldown_until"]:
        return True
    return False

def record_match_against(user_id: int, opponent_id: int):
    now = datetime.utcnow()
    if user_id not in recent_opponents:
        recent_opponents[user_id] = {}
    for other in list(recent_opponents[user_id].keys()):
        if other != opponent_id:
            recent_opponents[user_id][other] = {"count": 0, "cooldown_until": now}
            reset_cooldown_db(user_id, other)
    if opponent_id not in recent_opponents[user_id]:
        recent_opponents[user_id][opponent_id] = {"count": 0, "cooldown_until": now}
    entry = recent_opponents[user_id][opponent_id]
    if now >= entry["cooldown_until"]:
        entry["count"] += 1
    minutes = get_cooldown_minutes(entry["count"])
    if minutes:
        entry["cooldown_until"] = now + timedelta(minutes=minutes)
    save_cooldown(user_id, opponent_id, entry["count"], entry["cooldown_until"])

# ─── QUEUE POOL ──────────────────────────────────────────────────────────────

active_queues = {}
active_matches = {}
help_cooldowns = {}

class QueueEntry:
    def __init__(self, user_id, region, ability, set_type, elo, joined_at):
        self.user_id = user_id
        self.region = region
        self.ability = ability
        self.set_type = set_type
        self.elo = elo
        self.joined_at = joined_at

# ─── BOT SETUP ───────────────────────────────────────────────────────────────

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix=" ! ", intents=intents)

@bot.event
async def on_ready():
    load_cooldowns()
    load_ex_team()
    cursor.execute("SELECT COUNT(*) FROM seasons")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO seasons (season_number, started_at) VALUES (1, ?)",
                      (str(datetime.utcnow()),))
        conn.commit()
    await bot.tree.sync()
    print(f"{bot.user} is online!")

async def update_status():
    await bot.wait_until_ready()
    while not bot.is_closed():
        queue_count = len(active_queues)
        match_count = len(active_matches)
        if queue_count > 0:
            status = f"{queue_count} player(s) in queue"
        elif match_count > 0:
            status = f"Watching {match_count} match(es)"
        else:
            status = "OABD Ranked | /queue to play"
        await bot.change_presence(activity=discord.Game(name=status))
        await asyncio.sleep(30)

async def setup_hook():
    bot.loop.create_task(update_status())

bot.setup_hook = setup_hook

# ─── QUEUE COMMAND ───────────────────────────────────────────────────────────

@bot.tree.command(name="queue", description="Queue up for a Ranked 1v1 match")
async def queue(
    interaction: discord.Interaction,
    region: Region,
    ability: Ability,
    set_type: SetType
):
    if not is_queue_channel(interaction):
        await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
        return

    user_id = interaction.user.id

    if user_id in active_queues:
        await interaction.response.send_message("You are already in queue. Use `/leavequeue` to leave.", ephemeral=True)
        return

    in_active_match = any(
        user_id in [m["player1"], m["player2"]]
        for m in active_matches.values()
    )
    if in_active_match:
        await interaction.response.send_message("You are currently in an active match. Finish it before queuing again.", ephemeral=True)
        return

    create_player(user_id)
    player = get_player(user_id)
    elo = player[1]

    entry = QueueEntry(
        user_id=user_id,
        region=region.value,
        ability=ability.value,
        set_type=set_type.value,
        elo=elo,
        joined_at=datetime.utcnow()
    )
    active_queues[user_id] = entry

    await interaction.response.send_message(
        f"You joined the queue!\nRegion: {region.value} | Ability: {ability.value} | Set Type: {set_type.value}",
        ephemeral=True
    )

    asyncio.create_task(find_match(interaction.guild, entry))

# ─── MATCHMAKING ─────────────────────────────────────────────────────────────

async def find_match(guild: discord.Guild, entry: QueueEntry):
    while entry.user_id in active_queues:
        seconds_waiting = (datetime.utcnow() - entry.joined_at).total_seconds()

        if seconds_waiting < 300:
            allowed_regions = [entry.region]
        else:
            allowed_regions = REGION_PRIORITY[entry.region]

        for other_id, other in list(active_queues.items()):
            if other_id == entry.user_id:
                continue
            if other.region not in allowed_regions:
                continue
            if seconds_waiting < 30 and other.set_type != entry.set_type:
                continue

            if is_ex_team(entry.user_id) or is_ex_team(other.user_id):
                if abs(entry.elo - other.elo) > 300:
                    continue
            else:
                if abs(entry.elo - other.elo) > 200:
                    continue

            if is_on_cooldown(entry.user_id, other.user_id) or is_on_cooldown(other.user_id, entry.user_id):
                continue

            if entry.set_type == other.set_type:
                chosen_set = entry.set_type
                set_note = f"Set Type: {chosen_set}"
            else:
                chosen_set = random.choice([entry.set_type, other.set_type])
                set_note = f"Set Type: {chosen_set} *(decided by coinflip)*"

            active_queues.pop(entry.user_id, None)
            active_queues.pop(other_id, None)

            await create_match_channel(guild, entry, other, chosen_set, set_note)
            return

        await asyncio.sleep(10)

@bot.tree.command(name="leavequeue", description="Leave the matchmaking queue")
async def leavequeue(interaction: discord.Interaction):
    if not is_queue_channel(interaction):
        await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
        return

    user_id = interaction.user.id
    if user_id in active_queues:
        active_queues.pop(user_id)
        await interaction.response.send_message("You left the queue.", ephemeral=True)
    else:
        await interaction.response.send_message("You are not in queue.", ephemeral=True)

# ─── MATCH CHANNEL ───────────────────────────────────────────────────────────

async def create_match_channel(guild: discord.Guild, player1: QueueEntry, player2: QueueEntry, chosen_set: str, set_note: str):
    category = discord.utils.get(guild.categories, name=MATCH_CATEGORY_NAME)
    rover_role = discord.utils.get(guild.roles, name="RoVer Updater")

    member1 = guild.get_member(player1.user_id)
    member2 = guild.get_member(player2.user_id)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member1: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        member2: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }
    if rover_role:
        overwrites[rover_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    channel = await guild.create_text_channel(
        name=f"match-{member1.name}-vs-{member2.name}",
        category=category,
        overwrites=overwrites
    )

    cursor.execute("""
        INSERT INTO matches (player1_id, player2_id, channel_id, region, ability, set_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (player1.user_id, player2.user_id, channel.id, player1.region, player1.ability, chosen_set, str(datetime.utcnow())))
    conn.commit()

    active_matches[channel.id] = {
        "player1": player1.user_id,
        "player2": player2.user_id,
        "reports": {}
    }

    record_match_against(player1.user_id, player2.user_id)
    record_match_against(player2.user_id, player1.user_id)

    div1, lp1 = elo_to_division(player1.elo)
    div2, lp2 = elo_to_division(player2.elo)

    p1_rank = "👑 EX Team" if is_ex_team(player1.user_id) else f"{div1} {lp1} LP"
    p2_rank = "👑 EX Team" if is_ex_team(player2.user_id) else f"{div2} {lp2} LP"

    embed = discord.Embed(title="🎮 Match Found!", color=discord.Color.gold())
    embed.add_field(
        name=f"Player 1 — {member1.display_name}",
        value=f"**Rank:** {p1_rank}\n**Region:** {player1.region}\n**Ability:** {player1.ability}",
        inline=True
    )
    embed.add_field(name="VS", value="\u200b", inline=True)
    embed.add_field(
        name=f"Player 2 — {member2.display_name}",
        value=f"**Rank:** {p2_rank}\n**Region:** {player2.region}\n**Ability:** {player2.ability}",
        inline=True
    )
    embed.add_field(name="Set Type", value=set_note, inline=False)
    embed.set_footer(text="When the match is over, the winner uses /reportwin • Use /help for disputes")
    embed.timestamp = datetime.utcnow()

    await channel.send(content=f"{member1.mention} {member2.mention}", embed=embed)

# ─── REPORT WIN ──────────────────────────────────────────────────────────────

@bot.tree.command(name="reportwin", description="Report the winner of the match")
async def reportwin(interaction: discord.Interaction, winner: discord.Member):
    if not is_match_channel(interaction):
        await interaction.response.send_message("This command can only be used inside a match channel.", ephemeral=True)
        return

    channel_id = interaction.channel.id
    user_id = interaction.user.id

    if channel_id not in active_matches:
        await interaction.response.send_message("This is not an active match channel.", ephemeral=True)
        return

    match = active_matches[channel_id]

    if user_id not in [match["player1"], match["player2"]]:
        await interaction.response.send_message("You are not a player in this match.", ephemeral=True)
        return

    if winner.id not in [match["player1"], match["player2"]]:
        await interaction.response.send_message("You can only report one of the two players in this match as the winner.", ephemeral=True)
        return

    match["reports"][user_id] = winner.id

    if len(match["reports"]) == 2:
        reports = list(match["reports"].values())
        if reports[0] == reports[1]:
            winner_id = reports[0]
            loser_id = match["player2"] if winner_id == match["player1"] else match["player1"]
            await resolve_match(interaction, channel_id, winner_id, loser_id)
        else:
            await interaction.response.send_message(
                "⚠️ Both players reported different winners. Please use `/help` to get staff involved."
            )
    else:
        await interaction.response.send_message(
            f"{interaction.user.mention} has reported {winner.mention} as the winner. Waiting for the other player to confirm."
        )

async def resolve_match(interaction, channel_id, winner_id, loser_id):
    winner = get_player(winner_id)
    loser = get_player(loser_id)

    winner_elo = winner[1]
    loser_elo = loser[1]
    winner_placements = winner[2]
    winner_ranked = winner[4]

    gain, loss = calculate_lp_change(winner_elo, loser_elo, winner_id)

    new_winner_elo = min(winner_elo + gain, 599)
    current_division = loser_elo // 100
    lp_after_loss = (loser_elo % 100) - loss

    if lp_after_loss < 0 and loser_elo >= 100:
        protection = get_demotion_protection(loser_id)
        if protection == 0:
            new_loser_elo = current_division * 100
            set_demotion_protection(loser_id, 1)
            await interaction.channel.send(
                f"🛡️ {interaction.guild.get_member(loser_id).mention} is on demotion protection — one more loss will demote them."
            )
        else:
            new_loser_elo = max(loser_elo - loss, 0)
            set_demotion_protection(loser_id, 0)
    else:
        new_loser_elo = max(loser_elo - loss, 0)
        set_demotion_protection(loser_id, 0)

    if is_ex_team(winner_id):
        rank_num, pts = get_ex_team_rank(winner_id)
        new_pts = pts + gain
        demoted = try_promote_to_ex_db(winner_id, new_pts)
        if demoted:
            demoted_member = interaction.guild.get_member(demoted)
            await interaction.channel.send(
                f"⬇️ {demoted_member.mention} has been removed from EX Team and dropped back to S Team."
            )
    elif winner_elo >= 500 and new_winner_elo >= 600:
        s_points = new_winner_elo - 500
        demoted = try_promote_to_ex_db(winner_id, s_points)
        if demoted:
            demoted_member = interaction.guild.get_member(demoted)
            await interaction.channel.send(
                f"⬇️ {demoted_member.mention} has been removed from EX Team and dropped back to S Team."
            )
        new_winner_elo = 599

    if not winner_ranked:
        new_placements = winner_placements + 1
        cursor.execute("""
            UPDATE players SET placements_played = placements_played + 1,
            placements_won = placements_won + 1, elo = ?
            WHERE user_id = ?
        """, (new_winner_elo, winner_id))
        if new_placements >= 10:
            wins = winner[3] + 1
            placement_elo = round((wins / 10) * 250)
            placement_elo = max(0, min(placement_elo, 250))
            cursor.execute("UPDATE players SET ranked = 1, elo = ? WHERE user_id = ?", (placement_elo, winner_id))
    else:
        update_elo(winner_id, new_winner_elo)

    loser_data = get_player(loser_id)
    if not loser_data[4]:
        new_loser_placements = loser_data[2] + 1
        cursor.execute("""
            UPDATE players SET placements_played = placements_played + 1, elo = ?
            WHERE user_id = ?
        """, (new_loser_elo, loser_id))
        if new_loser_placements >= 10:
            wins = loser_data[3]
            placement_elo = round((wins / 10) * 250)
            placement_elo = max(0, min(placement_elo, 250))
            cursor.execute("UPDATE players SET ranked = 1, elo = ? WHERE user_id = ?", (placement_elo, loser_id))
    else:
        update_elo(loser_id, new_loser_elo)

    if is_ex_team(loser_id) and new_loser_elo < 500:
        remove_ex_team(loser_id)
        await interaction.channel.send(
            f"⬇️ {interaction.guild.get_member(loser_id).mention} has dropped out of EX Team."
        )

    add_win(winner_id)
    add_loss(loser_id)
    cursor.execute("""
        UPDATE matches SET winner_id_final = ?, lp_change = ?
        WHERE channel_id = ?
    """, (winner_id, gain, channel_id))
    conn.commit()

    winner_div, winner_lp = elo_to_division(new_winner_elo)
    loser_div, loser_lp = elo_to_division(new_loser_elo)

    winner_rank_str = f"👑 EX Team #{get_ex_team_rank(winner_id)[0]}" if is_ex_team(winner_id) else f"{winner_div} {winner_lp} LP"
    loser_rank_str = f"👑 EX Team #{get_ex_team_rank(loser_id)[0]}" if is_ex_team(loser_id) else f"{loser_div} {loser_lp} LP"

    winner_member = interaction.guild.get_member(winner_id)
    loser_member = interaction.guild.get_member(loser_id)

    embed = discord.Embed(title="✅ Match Result Confirmed", color=discord.Color.green())
    embed.add_field(name="🏆 Winner", value=f"{winner_member.mention}\n+{gain} LP → {winner_rank_str}", inline=True)
    embed.add_field(name="❌ Loser", value=f"{loser_member.mention}\n-{loss} LP → {loser_rank_str}", inline=True)
    embed.set_footer(text="This channel will be deleted in 60 seconds.")
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed)

    active_matches.pop(channel_id, None)

    await asyncio.sleep(60)
    channel = interaction.guild.get_channel(channel_id)
    if channel:
        await channel.delete()

# ─── HELP COMMAND ────────────────────────────────────────────────────────────

@bot.tree.command(name="help", description="Request staff help for a match dispute")
async def help_command(interaction: discord.Interaction):
    if not is_match_channel(interaction):
        await interaction.response.send_message("This command can only be used inside a match channel.", ephemeral=True)
        return

    channel_id = interaction.channel.id
    now = datetime.utcnow()

    if channel_id in help_cooldowns:
        seconds_since = (now - help_cooldowns[channel_id]).total_seconds()
        if seconds_since < 300:
            remaining = int(300 - seconds_since)
            await interaction.response.send_message(
                f"Staff were already notified. Please wait {remaining} seconds before using this again.",
                ephemeral=True
            )
            return

    help_cooldowns[channel_id] = now
    rover_role = discord.utils.get(interaction.guild.roles, name="RoVer Updater")

    if rover_role:
        await interaction.response.send_message(
            f"{rover_role.mention} — {interaction.user.mention} is requesting help in this match channel."
        )
    else:
        await interaction.response.send_message("Staff have been notified about a dispute in this channel.")

# ─── RANK COMMAND ────────────────────────────────────────────────────────────

@bot.tree.command(name="rank", description="Check your current rank and LP")
async def rank(interaction: discord.Interaction, member: discord.Member = None):
    if not is_queue_channel(interaction):
        await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
        return

    target = member or interaction.user
    user_id = target.id

    create_player(user_id)
    player = get_player(user_id)
    elo = player[1]
    placements_played = player[2]
    placements_won = player[3]
    ranked = player[4]

    create_stats(user_id)
    stats_data = get_stats(user_id)
    wins = stats_data[1] if stats_data else 0
    losses = stats_data[2] if stats_data else 0
    total = wins + losses
    winrate = round((wins / total) * 100, 1) if total > 0 else 0

    embed = discord.Embed(color=discord.Color.gold() if is_ex_team(user_id) else discord.Color.blurple())
    embed.set_author(name=f"{target.display_name}'s Rank", icon_url=target.display_avatar.url)
    embed.set_thumbnail(url=target.display_avatar.url)

    if not ranked:
        embed.title = "🔘 Unranked"
        embed.add_field(name="Placements", value=f"{placements_played}/10 completed", inline=True)
        embed.add_field(name="Placement Wins", value=str(placements_won), inline=True)
    elif is_ex_team(user_id):
        rank_num, pts = get_ex_team_rank(user_id)
        embed.title = f"👑 EX Team — Rank #{rank_num}"
        embed.add_field(name="Points", value=str(pts), inline=True)
    else:
        division, lp = elo_to_division(elo)
        embed.title = f"🏅 {division}"
        embed.add_field(name="LP", value=f"{lp} / 100", inline=True)
        embed.add_field(name="ELO", value=str(elo), inline=True)

    embed.add_field(name="Record", value=f"{wins}W / {losses}L", inline=True)
    embed.add_field(name="Win Rate", value=f"{winrate}%", inline=True)
    embed.set_footer(text="OABD Ranked")

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ─── STATS COMMAND ───────────────────────────────────────────────────────────

@bot.tree.command(name="stats", description="Check your win/loss record")
async def stats(interaction: discord.Interaction):
    if not is_queue_channel(interaction):
        await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
        return

    user_id = interaction.user.id
    create_stats(user_id)
    data = get_stats(user_id)
    wins = data[1]
    losses = data[2]
    total = wins + losses
    winrate = round((wins / total) * 100, 1) if total > 0 else 0

    await interaction.response.send_message(
        f"📊 **Stats for {interaction.user.display_name}**\n"
        f"Wins: {wins} | Losses: {losses} | Total: {total}\n"
        f"Win Rate: {winrate}%",
        ephemeral=True
    )

# ─── INFO / PROFILE COMMAND ──────────────────────────────────────────────────

@bot.tree.command(name="info", description="View your full OABD Ranked profile")
async def info(interaction: discord.Interaction, member: discord.Member = None):
    if not is_queue_channel(interaction):
        await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
        return

    target = member or interaction.user
    user_id = target.id

    create_player(user_id)
    create_stats(user_id)

    player = get_player(user_id)
    stats_data = get_stats(user_id)

    elo = player[1]
    placements_played = player[2]
    placements_won = player[3]
    ranked = player[4]

    wins = stats_data[1]
    losses = stats_data[2]
    total = wins + losses
    winrate = round((wins / total) * 100, 1) if total > 0 else 0

    cursor.execute("SELECT bio, joined_at FROM profiles WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    bio = profile[0] if profile and profile[0] else "No bio set."
    joined_at = profile[1] if profile and profile[1] else "Unknown"

    if not ranked:
        rank_str = f"Unranked ({placements_played}/10 placements)"
    elif is_ex_team(user_id):
        rank_num, pts = get_ex_team_rank(user_id)
        rank_str = f"👑 EX Team — Rank #{rank_num} ({pts} pts)"
    else:
        division, lp = elo_to_division(elo)
        rank_str = f"🏅 {division} — {lp} LP"

    cursor.execute("""
        SELECT set_type, COUNT(*) as count
        FROM matches
        WHERE player1_id = ? OR player2_id = ?
        GROUP BY set_type ORDER BY count DESC LIMIT 1
    """, (user_id, user_id))
    fav_set = cursor.fetchone()
    fav_set_str = fav_set[0] if fav_set else "N/A"

    cursor.execute("SELECT preferred_region, preferred_ability FROM profiles WHERE user_id = ?", (user_id,))
    prefs = cursor.fetchone()
    pref_region = prefs[0] if prefs and prefs[0] else "Not set"
    pref_ability = prefs[1] if prefs and prefs[1] else "Not set"

    embed = discord.Embed(
        title=f"⚔️ {target.display_name}'s Profile",
        color=discord.Color.gold() if is_ex_team(user_id) else discord.Color.blurple()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Rank", value=rank_str, inline=False)
    embed.add_field(name="Record", value=f"{wins}W / {losses}L ({winrate}% WR)", inline=False)
    embed.add_field(name="Placements", value=f"{placements_played}/10 played | {placements_won} won", inline=False)
    embed.add_field(name="Favourite Set Type", value=fav_set_str, inline=False)
    embed.add_field(name="Bio", value=bio, inline=False)
    embed.add_field(name="Preferred Region", value=pref_region, inline=True)
    embed.add_field(name="Preferred Ability", value=pref_ability, inline=True)
    embed.set_footer(text=f"OABD Ranked • Member since {joined_at}")

    await interaction.response.send_message(embed=embed)

# ─── LEADERBOARD COMMAND ─────────────────────────────────────────────────────

@bot.tree.command(name="leaderboard", description="See the top ranked players or players in your division")
async def leaderboard(interaction: discord.Interaction, division: str = None):
    if not is_queue_channel(interaction):
        await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    if division and division.title() not in DIVISIONS and division.upper() != "EX TEAM":
        await interaction.followup.send(
            f"Invalid division. Choose from: {', '.join(DIVISIONS)} or EX Team",
            ephemeral=True
        )
        return

    if division and division.upper() == "EX TEAM":
        if not ex_team_roster:
            await interaction.followup.send("No EX Team players yet.", ephemeral=True)
            return
        sorted_ex = sorted(ex_team_roster.items(), key=lambda x: x[1], reverse=True)
        embed = discord.Embed(title="👑 EX Team Leaderboard", color=discord.Color.gold())
        lines = []
        for i, (uid, pts) in enumerate(sorted_ex):
            member = interaction.guild.get_member(uid)
            name = member.display_name if member else f"User {uid}"
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}"
            lines.append(f"{medal} **{name}** — {pts} pts")
        embed.description = "\n".join(lines)
        embed.set_footer(text="OABD Ranked • EX Team Top 10")
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    cursor.execute("SELECT user_id, elo FROM players WHERE ranked = 1 ORDER BY elo DESC")
    rows = cursor.fetchall()

    if division:
        div_title = division.title()
        div_index = DIVISIONS.index(div_title)
        min_elo = div_index * 100
        max_elo = min_elo + 99
        rows = [r for r in rows if min_elo <= r[1] <= max_elo]
        embed = discord.Embed(title=f"🏅 {div_title} Leaderboard", color=discord.Color.blurple())
    else:
        rows = rows[:10]
        embed = discord.Embed(title="🏆 Top 10 Leaderboard", color=discord.Color.blurple())

    if not rows:
        await interaction.followup.send("No players found.", ephemeral=True)
        return

    lines = []
    for i, (uid, elo) in enumerate(rows):
        member = interaction.guild.get_member(uid)
        name = member.display_name if member else f"User {uid}"
        div, lp = elo_to_division(elo)
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"#{i+1}"
        lines.append(f"{medal} **{name}** — {div} {lp} LP")

    embed.description = "\n".join(lines)
    embed.set_footer(text="OABD Ranked")
    await interaction.followup.send(embed=embed, ephemeral=True)

# ─── OVERRIDE COMMAND ────────────────────────────────────────────────────────

@bot.tree.command(name="override", description="Staff only: manually set the winner or cancel the match")
async def override(interaction: discord.Interaction, winner: discord.Member = None):
    if not is_match_channel(interaction):
        await interaction.response.send_message("This command can only be used inside a match channel.", ephemeral=True)
        return

    rover_role = discord.utils.get(interaction.guild.roles, name="RoVer Updater")
    if rover_role not in interaction.user.roles:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    channel_id = interaction.channel.id
    if channel_id not in active_matches:
        await interaction.response.send_message("This is not an active match channel.", ephemeral=True)
        return

    match = active_matches[channel_id]

    if winner is None:
        active_matches.pop(channel_id, None)
        await interaction.response.send_message(
            f"⚙️ Match cancelled by {interaction.user.mention}. No LP changes. This channel will be deleted in 30 seconds."
        )
        await asyncio.sleep(30)
        channel = interaction.guild.get_channel(channel_id)
        if channel:
            await channel.delete()
        return

    if winner.id not in [match["player1"], match["player2"]]:
        await interaction.response.send_message("That player is not in this match.", ephemeral=True)
        return

    winner_id = winner.id
    loser_id = match["player2"] if winner_id == match["player1"] else match["player1"]

    await interaction.channel.send(
        f"⚙️ Staff override by {interaction.user.mention}: {winner.mention} has been declared the winner."
    )

    await resolve_match(interaction, channel_id, winner_id, loser_id)

# ─── QUEUE STATUS COMMAND ────────────────────────────────────────────────────

@bot.tree.command(name="queuestatus", description="See how many players are currently in queue")
async def queuestatus(interaction: discord.Interaction):
    if not is_queue_channel(interaction):
        await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
        return

    if not active_queues:
        embed = discord.Embed(title="📊 Queue Status", description="No players currently in queue.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    region_counts = {}
    set_counts = {}
    ability_counts = {}

    for entry in active_queues.values():
        region_counts[entry.region] = region_counts.get(entry.region, 0) + 1
        set_counts[entry.set_type] = set_counts.get(entry.set_type, 0) + 1
        ability_counts[entry.ability] = ability_counts.get(entry.ability, 0) + 1

    embed = discord.Embed(title="📊 Queue Status", color=discord.Color.green())
    embed.add_field(name="Players in Queue", value=str(len(active_queues)), inline=False)
    embed.add_field(name="By Region", value="\n".join(f"{r}: {c}" for r, c in region_counts.items()), inline=True)
    embed.add_field(name="By Set Type", value="\n".join(f"{s}: {c}" for s, c in set_counts.items()), inline=True)
    embed.add_field(name="By Ability", value="\n".join(f"{a}: {c}" for a, c in ability_counts.items()), inline=True)
    embed.add_field(name="Active Matches", value=str(len(active_matches)), inline=False)
    embed.set_footer(text="OABD Ranked")

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ─── SET PROFILE COMMAND ─────────────────────────────────────────────────────

@bot.tree.command(name="setprofile", description="Set your preferred region, ability, and bio")
async def setprofile(
    interaction: discord.Interaction,
    region: Region = None,
    ability: Ability = None,
    bio: str = None
):
    if not is_queue_channel(interaction):
        await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
        return

    user_id = interaction.user.id
    joined_at = datetime.utcnow().strftime("%Y-%m-%d")

    cursor.execute("""
        INSERT INTO profiles (user_id, display_name, bio, joined_at, preferred_region, preferred_ability)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            display_name = ?,
            bio = COALESCE(?, bio),
            preferred_region = COALESCE(?, preferred_region),
            preferred_ability = COALESCE(?, preferred_ability)
    """, (
        user_id, interaction.user.display_name, bio or "", joined_at,
        region.value if region else None, ability.value if ability else None,
        interaction.user.display_name, bio,
        region.value if region else None, ability.value if ability else None
    ))
    conn.commit()

    await interaction.response.send_message("Your profile has been updated.", ephemeral=True)

# ─── HISTORY COMMAND ─────────────────────────────────────────────────────────

@bot.tree.command(name="history", description="View your recent match history")
async def history(interaction: discord.Interaction, member: discord.Member = None):
    if not is_queue_channel(interaction):
        await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
        return

    target = member or interaction.user
    user_id = target.id

    cursor.execute("""
        SELECT player1_id, player2_id, winner_id_final, lp_change, set_type, created_at
        FROM matches
        WHERE (player1_id = ? OR player2_id = ?) AND winner_id_final IS NOT NULL
        ORDER BY created_at DESC LIMIT 10
    """, (user_id, user_id))
    rows = cursor.fetchall()

    if not rows:
        await interaction.response.send_message("No match history found.", ephemeral=True)
        return

    embed = discord.Embed(title=f"📋 Match History — {target.display_name}", color=discord.Color.blurple())

    for row in rows:
        player1_id, player2_id, winner_id_final, lp_change, set_type, created_at = row
        opponent_id = player2_id if user_id == player1_id else player1_id
        opponent = interaction.guild.get_member(opponent_id)
        opponent_name = opponent.display_name if opponent else f"User {opponent_id}"
        won = winner_id_final == user_id
        result = "✅ Win" if won else "❌ Loss"
        lp_str = f"+{lp_change}" if won else f"-{lp_change}"
        date = created_at[:10] if created_at else "Unknown"
        embed.add_field(
            name=f"{result} vs {opponent_name}",
            value=f"LP: {lp_str} | Set: {set_type} | {date}",
            inline=False
        )

    embed.set_footer(text="OABD Ranked • Last 10 matches")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ─── SEASON COMMANDS ─────────────────────────────────────────────────────────

@bot.tree.command(name="season", description="View current season info")
async def season(interaction: discord.Interaction):
    if not is_queue_channel(interaction):
        await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
        return

    current_season, started_at = get_current_season()
    started_date = started_at[:10] if started_at and started_at != "Unknown" else "Unknown"

    cursor.execute("SELECT COUNT(*) FROM players WHERE ranked = 1")
    ranked_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM players")
    total_count = cursor.fetchone()[0]

    embed = discord.Embed(title=f"📆 Season {current_season}", color=discord.Color.gold())
    embed.add_field(name="Started", value=started_date, inline=True)
    embed.add_field(name="Ranked Players", value=str(ranked_count), inline=True)
    embed.add_field(name="Total Players", value=str(total_count), inline=True)
    embed.add_field(name="Active Matches", value=str(len(active_matches)), inline=True)
    embed.add_field(name="Players in Queue", value=str(len(active_queues)), inline=True)
    embed.set_footer(text="OABD Ranked")
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="seasonhistory", description="View your stats from a previous season")
async def seasonhistory(interaction: discord.Interaction, season: int = None, member: discord.Member = None):
    if not is_queue_channel(interaction):
        await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
        return

    target = member or interaction.user
    user_id = target.id

    if season:
        cursor.execute("""
            SELECT season_number, final_division, final_lp, wins, losses
            FROM season_history WHERE user_id = ? AND season_number = ?
        """, (user_id, season))
    else:
        cursor.execute("""
            SELECT season_number, final_division, final_lp, wins, losses
            FROM season_history WHERE user_id = ? ORDER BY season_number DESC LIMIT 5
        """, (user_id,))

    rows = cursor.fetchall()

    if not rows:
        await interaction.response.send_message("No season history found.", ephemeral=True)
        return

    current_season, _ = get_current_season()
    embed = discord.Embed(title=f"📅 Season History — {target.display_name}", color=discord.Color.blurple())

    for row in rows:
        season_num, division, lp, wins, losses = row
        total = wins + losses
        winrate = round((wins / total) * 100, 1) if total > 0 else 0
        embed.add_field(
            name=f"Season {season_num}",
            value=f"**Rank:** {division} {lp} LP\n**Record:** {wins}W / {losses}L ({winrate}% WR)",
            inline=False
        )

    embed.set_footer(text=f"Current Season: {current_season} • OABD Ranked")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ─── STAFF COMMANDS (no channel restriction) ─────────────────────────────────

@bot.tree.command(name="adjustlp", description="Staff only: manually adjust a player's LP")
async def adjustlp(interaction: discord.Interaction, member: discord.Member, amount: int):
    rover_role = discord.utils.get(interaction.guild.roles, name="RoVer Updater")
    if rover_role not in interaction.user.roles:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    create_player(member.id)
    player = get_player(member.id)
    old_elo = player[1]
    new_elo = max(0, min(old_elo + amount, 599))
    update_elo(member.id, new_elo)

    old_div, old_lp = elo_to_division(old_elo)
    new_div, new_lp = elo_to_division(new_elo)
    direction = "+" if amount >= 0 else ""

    embed = discord.Embed(title="⚙️ LP Adjusted", color=discord.Color.orange())
    embed.add_field(name="Player", value=member.mention, inline=False)
    embed.add_field(name="Before", value=f"{old_div} {old_lp} LP", inline=True)
    embed.add_field(name="After", value=f"{new_div} {new_lp} LP", inline=True)
    embed.add_field(name="Change", value=f"{direction}{amount} LP", inline=True)
    embed.set_footer(text=f"Adjusted by {interaction.user.display_name}")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="startseason", description="Start a new ranked season and soft reset all ELO")
async def startseason(interaction: discord.Interaction):
    if interaction.user.id not in SEASON_ADMINS:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer()

    current_season, started_at = get_current_season()
    new_season = current_season + 1

    cursor.execute("SELECT user_id, elo FROM players WHERE ranked = 1")
    all_players = cursor.fetchall()

    for user_id, elo in all_players:
        stats = get_stats(user_id)
        wins = stats[1] if stats else 0
        losses = stats[2] if stats else 0
        record_season_history(user_id, current_season, elo, wins, losses)

    cursor.execute("SELECT user_id, elo FROM players")
    all_rows = cursor.fetchall()
    for user_id, elo in all_rows:
        soft_elo = max(0, round(elo * 0.3))
        cursor.execute("""
            UPDATE players SET elo = ?, ranked = 0, placements_played = 0,
            placements_won = 0, demotion_protection = 0, season_number = ?
            WHERE user_id = ?
        """, (soft_elo, new_season, user_id))

    cursor.execute("UPDATE player_stats SET wins = 0, losses = 0")
    cursor.execute("DELETE FROM ex_team")
    ex_team_roster.clear()
    cursor.execute("INSERT INTO seasons (season_number, started_at) VALUES (?, ?)",
                  (new_season, str(datetime.utcnow())))
    cursor.execute("UPDATE seasons SET ended_at = ? WHERE season_number = ?",
                  (str(datetime.utcnow()), current_season))
    conn.commit()

    embed = discord.Embed(
        title=f"🏁 Season {new_season} Has Begun!",
        description=f"Season {current_season} has ended. All rankings have been soft reset.",
        color=discord.Color.gold()
    )
    embed.add_field(name="Players Recorded", value=str(len(all_players)), inline=True)
    embed.add_field(name="New Season", value=str(new_season), inline=True)
    embed.add_field(name="How Soft Reset Works", value="Players keep 30% of their previous ELO and must complete placements again.", inline=False)
    embed.set_footer(text=f"Season started by {interaction.user.display_name}")
    embed.timestamp = datetime.utcnow()

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="resetplayer", description="Staff only: wipe a player's data entirely")
async def resetplayer(interaction: discord.Interaction, member: discord.Member):
    rover_role = discord.utils.get(interaction.guild.roles, name="RoVer Updater")
    if rover_role not in interaction.user.roles:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    user_id = member.id
    active_queues.pop(user_id, None)

    if is_ex_team(user_id):
        remove_ex_team(user_id)

    cursor.execute("DELETE FROM players WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM player_stats WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM farming_cooldowns WHERE user_id = ? OR opponent_id = ?", (user_id, user_id))
    cursor.execute("DELETE FROM season_history WHERE user_id = ?", (user_id,))
    conn.commit()

    recent_opponents.pop(user_id, None)
    for uid in recent_opponents:
        recent_opponents[uid].pop(user_id, None)

    embed = discord.Embed(title="🗑️ Player Reset", color=discord.Color.red())
    embed.add_field(name="Player", value=member.mention, inline=False)
    embed.add_field(name="Data Wiped", value="ELO, stats, profile, cooldowns, season history", inline=False)
    embed.set_footer(text=f"Reset by {interaction.user.display_name}")
    embed.timestamp = datetime.utcnow()

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="resetfarming", description="Staff only: reset all anti-farming cooldowns")
async def resetfarming(interaction: discord.Interaction):
    rover_role = discord.utils.get(interaction.guild.roles, name="RoVer Updater")
    if rover_role not in interaction.user.roles:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return

    recent_opponents.clear()
    cursor.execute("DELETE FROM farming_cooldowns")
    conn.commit()

    await interaction.response.send_message("✅ All anti-farming cooldowns have been reset.", ephemeral=True)

bot.run(TOKEN)