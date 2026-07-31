"""Event / MO4 commands: mo4, event_start, event_end, submit_to, submit."""
import os
import json
import time
import datetime

from discord.ext import commands

from helpers import custom_cooldown
from utils import cooldown_error_handler, increment_counter_file
from ocr import img_to_stats, summary_from_stats
from icon_detect import detect_helldiver_icon
from config import EVENTS_DIR


def _read_counter(filepath):
    """Read an integer counter file, returning 0 if missing."""
    if os.path.isfile(filepath):
        with open(filepath, 'r') as f:
            content = f.read().strip()
            return int(content) if content else 0
    return 0


def gen_mo4_progress():
    """Generate MO4 objective progress message (stats + TO sections)."""
    mo4_ddl = 1785662059
    sections = []

    # --- Stats-based objectives (event.json) ---
    if os.path.isfile(os.path.join(EVENTS_DIR, 'event.json')):
        total_kills = _read_counter(os.path.join(EVENTS_DIR, 'kills.txt'))
        total_deaths = _read_counter(os.path.join(EVENTS_DIR, 'deaths.txt'))
        total_shots = _read_counter(os.path.join(EVENTS_DIR, 'shots.txt'))
        total_hits = _read_counter(os.path.join(EVENTS_DIR, 'hits.txt'))
        total_samples = _read_counter(os.path.join(EVENTS_DIR, 'samples.txt'))

        kdr = total_kills / total_deaths if total_deaths > 0 else float(total_kills)
        accuracy = (total_hits / total_shots * 100) if total_shots > 0 else 0.0

        goal_kills = 150000
        goal_kdr = 500
        goal_accuracy = 90
        goal_samples = 500

        objectives_met = (
            total_kills >= goal_kills
            and kdr >= goal_kdr
            and accuracy >= goal_accuracy
            and total_samples >= goal_samples
        )

        state = 'Ongoing'
        if time.time() >= mo4_ddl:
            state = 'Success' if objectives_met else 'Failure'

        sections.append(
            f"## MO4: {state}\n"
            f"Ends: <t:{mo4_ddl}:R>\n"
            f"- Kills: **{total_kills}**/{goal_kills}\n"
            f"- KDR: **{kdr:.1f}**/{goal_kdr}\n"
            f"- Accuracy: **{accuracy:.1f}%**/{goal_accuracy}%\n"
            f"- Samples Collected: **{total_samples}**/{goal_samples}"
        )

        if state != 'Ongoing':
            os.rename(
                os.path.join(EVENTS_DIR, 'event.json'),
                os.path.join(EVENTS_DIR, f'm04_13_{state.lower()}.json')
            )

    # --- TO-based objectives (event_to.json) ---
    if os.path.isfile(os.path.join(EVENTS_DIR, 'event_to.json')):
        with open(os.path.join(EVENTS_DIR, 'event_to.json'), 'r') as f:
            TO_LOGS = json.load(f)

        goal_air = 150
        goal_evac = 50

        count_air = 0
        count_evac = 0
        for player in TO_LOGS:
            count_air += TO_LOGS[player].get('Restore_Air_Quality', 0)
            count_evac += TO_LOGS[player].get('Emergency_Evacuation', 0)

        to_met = count_air >= goal_air and count_evac >= goal_evac

        to_state = 'Ongoing'
        if time.time() >= mo4_ddl:
            to_state = 'Success' if to_met else 'Failure'

        sections.append(
            f"## SO4: {to_state}\n"
            f"Ends: <t:{mo4_ddl}:R>\n"
            f"- Air Quality Restored: **{count_air}**/{goal_air}\n"
            f"- Colonist Groups Evacuated: **{count_evac}**/{goal_evac}"
        )

        if to_state != 'Ongoing':
            os.rename(
                os.path.join(EVENTS_DIR, 'event_to.json'),
                os.path.join(EVENTS_DIR, f'm04_13_{to_state.lower()}_to.json')
            )

    if not sections:
        return None

    return '\n\n'.join(sections)


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='mo4')
    @commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
    async def mo4_progress_command(self, ctx):
        msg = gen_mo4_progress()
        if msg is None:
            return await ctx.reply("```No ongoing MO4 event.```")
        await ctx.reply(msg)

    @mo4_progress_command.error
    async def mo4_error(self, ctx, error):
        await cooldown_error_handler()(ctx, error)

    @commands.command(name='event_start')
    @commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
    async def event_start(self, ctx, to: str):
        start_time = time.time()
        with open(os.path.join(EVENTS_DIR, 'start.txt'), 'w') as f:
            f.write(str(int(start_time)))
        init_json = {}
        if to == 'to':
            with open(os.path.join(EVENTS_DIR, 'event_to.json'), 'w') as f:
                json.dump(init_json, f)
            return await ctx.reply("TO Event initiated.")
        with open(os.path.join(EVENTS_DIR, 'event.json'), 'w') as f:
            json.dump(init_json, f)
        for counter in ('kills.txt', 'deaths.txt', 'shots.txt', 'hits.txt', 'samples.txt'):
            with open(os.path.join(EVENTS_DIR, counter), 'w') as f:
                f.write('0')
        return await ctx.reply("Event initiated.")

    @commands.command(name='event_end')
    @commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
    async def event_end(self, ctx):
        archive = os.path.join(EVENTS_DIR, f"archived_event_{datetime.datetime.now()}.json")
        archive_to = os.path.join(EVENTS_DIR, f"archived_event_to_{datetime.datetime.now()}.json")
        if os.path.isfile(os.path.join(EVENTS_DIR, 'event.json')):
            os.rename(os.path.join(EVENTS_DIR, "event.json"), archive)
            await ctx.reply('Event ended.')
        if os.path.isfile(os.path.join(EVENTS_DIR, 'event_to.json')):
            os.rename(os.path.join(EVENTS_DIR, "event_to.json"), archive_to)
            await ctx.reply("TO Event ended.")

    @commands.command(name='submit_to')
    async def submit_to_command(self, ctx):
        if not os.path.isfile(os.path.join(EVENTS_DIR, 'event_to.json')):
            return await ctx.reply("```No ongoing TO-based MO4.```")
        usr = str(ctx.author.id)
        if not ctx.message.attachments:
            return await ctx.reply("```No image attachment detected, please retry.```")
        if len(ctx.message.attachments) > 1:
            return await ctx.reply("```More than one attachment detected, please retry.```")
        imgcache_dir = os.path.join(EVENTS_DIR, 'imgcache')
        if not os.path.isdir(imgcache_dir):
            os.mkdir(imgcache_dir)

        img = ctx.message.attachments[0]
        content_type = img.content_type
        if not content_type.startswith('image'):
            return await ctx.reply("```No image attachment detected, please retry.```")
        suffix = content_type.split('/')[1]
        filename = os.path.join(imgcache_dir, f"{usr}.{suffix}")
        await img.save(fp=filename)
        matches, obj_matches = detect_helldiver_icon(filename)
        for icon, value in obj_matches.items():
            if icon in matches:
                matches[icon] += value
            else:
                matches[icon] = value
        if 'Sabotage_Air_Base_2' in matches:
            matches['Sabotage_Air_Base'] = 1
        player = ctx.author.display_name
        with open(os.path.join(EVENTS_DIR, 'event_to.json'), 'r') as f:
            LOGS = json.load(f)
        if player not in LOGS:
            LOGS[player] = matches
        else:
            for to in matches:
                if to not in LOGS[player]:
                    LOGS[player][to] = matches[to]
                else:
                    LOGS[player][to] += matches[to]
        with open(os.path.join(EVENTS_DIR, 'event_to.json'), 'w') as f:
            json.dump(LOGS, f)
        formatted = '\n'.join([f"{name}:\t{count}" for name, count in matches.items()])
        return await ctx.reply(f"```{formatted}```\nMission logged.")

    @commands.command(name='submit')
    async def submit_stats(self, ctx, idx: str):
        if idx not in ['1', '2', '3', '4']:
            return await ctx.reply("```Incorrect format. Please indicate which are your stats (counting from the left) in the screenshot, e.g. $submit 2```")
        idx = int(idx) - 1
        if not os.path.isfile(os.path.join(EVENTS_DIR, 'event.json')):
            return await ctx.reply("```No ongoing stats-based MO4.```")
        usr = str(ctx.author.id)
        if not ctx.message.attachments:
            return await ctx.reply("```No image attachment detected, please retry.```")
        if len(ctx.message.attachments) > 1:
            return await ctx.reply("```More than one attachment detected, please retry.```")

        imgcache_dir = os.path.join(EVENTS_DIR, 'imgcache')
        if not os.path.isdir(imgcache_dir):
            os.mkdir(imgcache_dir)

        img = ctx.message.attachments[0]
        content_type = img.content_type
        if not content_type.startswith('image'):
            return await ctx.reply("```No image attachment detected, please retry.```")
        suffix = content_type.split('/')[1]
        filename = os.path.join(imgcache_dir, f"{usr}.{suffix}")
        await img.save(fp=filename)
        stats = img_to_stats(filename)
        summary = summary_from_stats(stats)
        player = ctx.author.display_name

        player_stats = {}
        for stat in stats:
            player_stats[stat] = stats[stat][idx]

        kills = int(sum([int(i) for i in stats['KILLS'] if i != 'N/A']))
        increment_counter_file(os.path.join(EVENTS_DIR, 'kills.txt'), kills)

        deaths = int(sum([int(i) for i in stats['DEATHS'] if i != 'N/A']))
        increment_counter_file(os.path.join(EVENTS_DIR, 'deaths.txt'), deaths)

        shots = int(sum([int(i) for i in stats['SHOTS FIRED'] if i != 'N/A']))
        increment_counter_file(os.path.join(EVENTS_DIR, 'shots.txt'), shots)

        hits = int(sum([int(i) for i in stats['SHOTS HIT'] if i != 'N/A']))
        increment_counter_file(os.path.join(EVENTS_DIR, 'hits.txt'), hits)

        samples = int(sum([int(i) for i in stats['SAMPLES EXTRACTED'] if i != 'N/A']))
        increment_counter_file(os.path.join(EVENTS_DIR, 'samples.txt'), samples)

        with open(os.path.join(EVENTS_DIR, 'event.json'), 'r') as f:
            LOGS = json.load(f)

        if player not in LOGS:
            LOGS[player] = {}
            for stat in player_stats:
                LOGS[player][stat] = [player_stats[stat]]
        else:
            for stat in LOGS[player]:
                if stat not in player_stats:
                    LOGS[player][stat].append('N/A')
                else:
                    LOGS[player][stat].append(player_stats[stat])

        with open(os.path.join(EVENTS_DIR, 'event.json'), 'w') as f:
            json.dump(LOGS, f)
        return await ctx.reply(f"```{summary}```\nYour stats have been logged for analysis.")


async def setup(bot):
    await bot.add_cog(Events(bot))
