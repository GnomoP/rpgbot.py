#!/usr/bin/env python3.6

import re
import os
import sys
import time
import json
import asyncio
import logging
from random import randrange
from datetime import datetime
from subprocess import Popen, PIPE
import discord
from discord import abc
from discord.ext import commands
from client import Client
from inventory import Inventory
from bot_utils import initlog, trim_codeblocks
from json_utils import json_load, json_dump, json_dumps


config_fp = os.path.dirname(os.path.realpath(__file__)) + "/config.json"
bot = Client(config_fp)


async def del_or_pin(org_message, message, time=10.0):
  await message.add_reaction('📌')
  await message.add_reaction('❌')

  def check(react, user):
    a = user.id == org_message.author.id
    b = str(react.emoji) in ('📌', '❌')
    c = react.message.id == message.id
    return a and b and c

  try:
    react, user = await bot.wait_for("reaction_add", timeout=time, check=check)
  except asyncio.TimeoutError:
    try:
      await message.delete()
      await org_message.delete()
    except Exception as e:
      pass
    return
  react = str(react.emoji)

  def check(react, user):
    a = user.id == org_message.author.id
    b = str(react.emoji) == '📌'
    c = react.message.id == message.id
    return a and b and c

  if react == '📌':
    react, user = await bot.wait_for("reaction_remove", check=check)
  elif react == '❌':
    pass
  else:
    await asyncio.sleep(time)

  try:
    await message.delete()
    await org_message.delete()
  except Exception as e:
    pass


async def yesno_diag(message, default: bool=False, time=10.0):
  await message.add_reaction('👍')
  await message.add_reaction('👎')

  def check(react, user):
    a = user.id == message.author.id
    b = str(react.emoji) in ('👍', '👎')
    c = react.message.id == message.id
    return a and b and c

  try:
    react, user = await bot.wait_for("reaction_add", timeout=time, check=check)
  except asyncio.TimeoutError:
    return default
  react = str(react.emoji)

  if react == '👍':
    return True
  else:
    return False


async def throw_die(channel: abc.Messageable, die=int):
  out = "Rolled **{0}** from a D{1}"

  # Truncate to 1000 and add decimal places
  if die > 1000:
    die = 1000
    val = randrange(1, 1001) + (randrange(0, 1000) * 0.001)
    out + " ".join([
      "Rolled **{0}**."
      "\n\***(Number of sides ({1}) is over 1000.",
      "Truncating to 1000 and adding decimal places)**"])

  # Truncate to 2 (heads and tails)
  elif die <= 1:
    die = 2
    val = int(randrange(1, 3))
    out += " ".join([
      "\n\***(Number of sides is under 2.",
      "Truncating to heads and tails)**"])

  # Roll N-sided die
  else:
    val = int(randrange(1, die + 1))

  return await channel.send(out.format(val, die))


@bot.event
async def on_connect():
  bot.print("Connected to Discord...")
  await bot.wait_until_ready()

  bot.print("Logged in as %s" % bot.user)
  bot.print("Command prefix: '%s'" % bot.command_prefix)

  game = discord.Game(bot.config["status"])
  await bot.change_presence(status=discord.Status.online, activity=game)


@bot.event
async def on_message(m):
  if bot.check_msg(m):
    await bot.process_commands(m)

  if bot.paused:
    return

  # Match die rolls for integers (D20, d-2, d 21, etc.)
  p = re.compile(r'^\s*[Dd][ +\-]*\d+\s*$')
  if p.match(m.clean_content):
    die = int(re.search(r'\d+', m.clean_content).group())
    msg = await throw_die(m.channel, die)
    await del_or_pin(m, msg, 20.0)

  # Access, modify or delete the inventory
  p = re.compile(r'^\s*inv(entory)* .*\s*$')
  if p.match(m.clean_content):
    pass


@bot.event
async def on_message_delete(m):
  if m.author.id in bot._wlist["users"] or m.author.id == bot.user.id:
    return

  if m.clean_content and not bot.paused:
    fmt = "\n".join([
      "```markdown",
      "# {0.name}#{0.discriminator} ({0.id}) deleted",
      "> {2}",
      "> {1}",
      "> End of Message",
      "```"
    ])

    date = datetime.now().strftime("%a, %d %b %Y %I:%M:%S %p %Z")
    content = m.clean_content.replace("\n", "\n> ")

    if not bot.config["announcements"]:
      return

    # Log to announcements channel
    ann = bot.get_channel(bot.config["announcements"])
    await ann.send(fmt.format(m.author, content, date))


@bot.event
async def on_member_join(member):
  if not bot.paused:
    for role in member.guild.roles:
      if role.name.startswith("Plebeu"):
        break
    await member.add_roles(role, reason="Plébe")

    # Log to announcements channel
    if not bot.config["announcements"]:
      return

    ann = bot.get_channel(bot.config["announcements"])
    await ann.send(
      "{0.mention} é um Plebeu. Siga as normas, *rusticus*.".format(member))


@bot.command(aliases=["inv"])
async def inventory(ctx, quant, *, item=None):
  p = r'^(\s*(\d+)|(\?{1})|(-{1})$'
  p = re.search(p, quant)

  if not p:
    await ctx.message.add_reaction("❗")
    bot.print("Bad value given to inventory command: '%s'" % quant)
    return

  fp = bot.rootfp + "/" + ctx.message.author.id + ".json"
  if not os.path.exists(fp):
    open(fp, "a+").close()

  with open(fp, "r+") as data:
    data.seek(0)
    if not data.read():
      data.write("{\n\n}")
      data.truncate()

    data.seek(0)
    inv = json_load(data, bot.print)

  item = item.lower() if item is not None else None
  if quant == "?":
    if item is None:
      out = "```json\n{}\n```".format(json_dumps(inv))
      if len(out) > 2000:
        out = out[:-10] + "\n...\n}```"
      m = await ctx.send(out)
      await bot.msgdiag_delpin(ctx, m, 10.0)
      return

    inum = inv.get(item, 0)

  elif quant == "-":
    inv.pop(item, None)

    with open(inv, "w") as data:
      json_dump(inv, data)

  else:
    if item is None:
      m = await ctx.send("`item is a required argument that is missing.`")
      await bot.msgdiag_delpin(ctx, m, 10.0)
      return

    inum = eval(quant)
    if float(inum).is_integer:
      inum = int(inum)
    inv[item] = inv.get(item, 0) + inum

    with open(fp, "w") as data:
      json_dump(inv, data)

  inum = inv.get(item, 0)
  fmt = "{0.display_name} has {1} '{2}'"
  m = await ctx.send(fmt.format(ctx.message.author, inum, item))
  await del_or_pin(ctx, m, 10.0)


@bot.command(aliases=["die", "d", "D"])
async def dice(ctx, *, die: int=20):
  msg = await throw_die(ctx.message.channel, die)
  await del_or_pin(ctx.message, msg, 20.0)

  await asyncio.sleep(bot.timeout) if bot.timeout else None

  try:
    await ctx.message.delete() if bot.timeout else None
  except Exception:
    pass


@commands.is_owner()
@bot.command(aliases=["bash", "sh"])
async def shell(ctx, *, script="notify-send -t 3 -i bash 'Bonk'"):
  try:
    await ctx.message.add_reaction('🐚')
  except Exception:
    pass

  script = trim_codeblocks(script)
  Popen(script, shell=True)


@bot.command(aliases=["py2", "python", "py"])
async def python2(ctx, *, pycode="import this"):
  pycode = trim_codeblocks(pycode)
  args = "{} << EOF\n{}\nEOF".format("python2", pycode)

  out, e = Popen(
    args,
    shell=True,
    stderr=PIPE,
    stdout=PIPE,
    stdin=PIPE
  ).communicate()

  out = out.decode("utf-8")
  e = e.decode("utf-8")

  if e:
    out += "\n" + "\n".join(e.splitlines())

  try:
    await ctx.send("```\n%s```" % out)
  except Exception as e:
    await ctx.message.add_reaction("❗")
    bot.print(e)


@bot.command(aliases=["py3"])
async def python3(ctx, *, pycode="import this"):
  pycode = trim_codeblocks(pycode)
  args = "{} << EOF\n{}\nEOF".format(sys.executable, pycode)

  out, e = Popen(
    args,
    shell=True,
    stderr=PIPE,
    stdout=PIPE,
    stdin=PIPE
  ).communicate()

  out = out.decode("utf-8")
  e = e.decode("utf-8")

  if e:
    out += "\n" + "\n".join(e.splitlines())

  try:
    await ctx.send("```\n%s```" % out)
  except Exception as e:
    await ctx.message.add_reaction("❗")
    bot.print(e)


if __name__ == "__main__":
  if len(sys.argv) < 2:
    fp = os.path.dirname(os.path.realpath(__file__)) + "/inv/config.json"
  else:
    fp = " ".join(sys.argv[1:])

  logger = initlog(json_load(fp, Client.print))
  bot()
