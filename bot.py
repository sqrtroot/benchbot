import discord
from discord.ext.commands import Bot, Context
from discord.ext.tasks import loop, Loop
from consts import BINARY_DIR
from db import *
import psutil
import re
from tabulate import tabulate
from hashlib import md5
from typing import Optional

EMPTY_CHAR = '﻿'

bot = Bot(command_prefix=">")


@loop(seconds=1, loop=bot.loop)
async def status():
    print('hoi')
    bot_status = discord.Status.dnd
    await bot.change_presence(status=bot_status,
                              activity=discord.Activity(
                                  type=discord.ActivityType.playing,
                                  name=f'Usage: {psutil.cpu_percent()}%'))


@bot.command()
async def ping(ctx: Context):
    await ctx.send(f"<@{ctx.author.id}> pong")


@bot.command()
@with_session
async def start(session: SessionT, ctx: Context):
    author = find_author(session, ctx.author.id)
    if author:
        await ctx.send(f"{ctx.author.mention} You have already registered")
    else:
        session.add(Contender(id=ctx.author.id, name=ctx.author.name))
        await ctx.send(f'Welcome to the challenges {ctx.author.mention}')


@bot.command(aliases=['bench', 'b'])
@with_session
async def benchmark(session: SessionT, ctx: Context, bench_name: Optional[str] = None):
    if not ctx.message.attachments:
        await ctx.send(f"{ctx.author.mention} Try attaching a binary!")
        return

    author = find_author(session, ctx.author.id)
    if not author:
        await ctx.send(
            f"{ctx.author.mention} You have not yet registered for the challenge!"
        )
        return
    attachment: discord.Attachment = ctx.message.attachments[0]

    max_size = 1024 * 1024 * 10  # 10 MiB
    if attachment.size > max_size:
        await ctx.send(
            f"{ctx.author.mention} I currently don't accept binaries larger than {max_size // 1024 ** 2} MiB"
        )
        return

    challenge = get_challenge(session, bench_name or attachment.filename)
    if not challenge:
        await ctx.send(
            f"{ctx.author.mention} I haven't heard about that challenge. Maybe check the active challenges"
        )
        return

    data = await attachment.read()
    hash = md5()
    hash.update(data)

    already_benched = session.query(Benchmark).filter(Benchmark.hash == hash.hexdigest())
    print(already_benched.first())
    if bench_result := already_benched.first():
        await ctx.send(f'Already benchmarked this file:\n```{bench_result.result_format()}```')
        return

    bench = Benchmark(challenge=session.merge(challenge),
                      contender=session.merge(author),
                      hash=hash.hexdigest(),
                      bin_size=attachment.size)
    session.add(bench)
    session.flush()

    filename = f'{BINARY_DIR}/{challenge.name}-{bench.id}'
    with open(filename, 'wb') as f:
        f.write(data)
    await ctx.send(f"Thank you {ctx.author.mention}, you'll soon be notified of the results")


@bot.command()
@with_session
async def challenges(session: SessionT, ctx: Context):
    chlngs = []
    for challenge in session.query(Challenge).filter(Challenge.active).all():
        chlngs.append((challenge.id, challenge.name))
    if chlngs:
        await ctx.send(f'{EMPTY_CHAR}\n```{tabulate(chlngs, headers=["Id", "Name"], tablefmt="fancy_grid")}```')
    else:
        await ctx.send("No active challenges at the moment")


@bot.listen()
async def on_message(message: discord.Message):
    if code := re.search(r'```(.*)```', message.content):
        if len(code.group(1)) > 50:
            print("long code found")
            pass


def notify_bench_done(user_id, challenge_name, bench_report):
    if bot.is_closed():
        return

    async def notify():
        user: discord.User = await bot.fetch_user(user_id)
        await user.send(f"Your benchmark for {challenge_name} is done")
        await user.send(f"{EMPTY_CHAR}\nYour results are:\n```{bench_report}```")

    bot.loop.create_task(notify())