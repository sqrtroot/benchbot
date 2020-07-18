import discord
from discord.ext.commands import Bot, Context
from consts import TOKEN, CODE_CHANNEL
import re
import db
import asyncio
awaits = lambda *f: asyncio.wait([*f])

bot = Bot(command_prefix=">")

@bot.command()
async def ping(ctx: Context):
    await ctx.send(f"<@{ctx.author.id}> pong")

@bot.command()
async def start(ctx:Context):
    req = db.contenders.select().where(db.contenders.c.id == ctx.author.id)
    result: db.Result = await db.connection.execute(req)
    found = await result.scalar()
    if found:
        await ctx.send(f"{ctx.author.mention} You've already registered")
    else:
        ins = db.contenders.insert().values(id=ctx.author.id, name=ctx.author.name)
        await awaits(db.connection.execute(ins),
                     ctx.send(f"Welcome to the challenges {ctx.author.mention}"))


@bot.listen()
async def on_message(message: discord.Message):
    if code := re.search(r'```(.*)```', message.content):
        if len(code.group(1)) > 50:
            print("long code found")
            pass


bot.loop.create_task(db.init_db())
bot.run(TOKEN)
