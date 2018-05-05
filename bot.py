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
# from inventory import Inventory
from bot_utils import initlog, trim_codeblocks
from json_utils import json_load, json_dump, json_dumps

root = os.path.dirname(os.path.realpath(__file__))

bot = Client(root + "/config.json")
# bot.inv = Inventory(root + "/inv/config.json")


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
      bot.print(e)
    return
  react = str(react.emoji)

  def check(react, user):
    a = user.id == org_message.author.id
    b = str(react.emoji) == '📌'
    c = react.message.id == message.id
    return a and b and c

  if react == '📌':
    await bot.wait_for("reaction_remove", check=check)
  elif react == '❌':
    pass
  else:
    await asyncio.sleep(time)

  try:
    await message.delete()
    await org_message.delete()
  except Exception as e:
    bot.print(e)


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
    val = randrange(1000) + (randrange(0, 1000) * 0.001)
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
  p = re.compile(r"^\s*[Dd][ +\-]*\d+\s*$")
  if p.match(m.clean_content):
    die = int(re.search(r"\d+", m.clean_content).group())
    msg = await throw_die(m.channel, die)
    await del_or_pin(m, msg, 20.0)


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


@bot.command(name="inv")
async def inventory(ctx, quant="?", *, item=None):
  p = r"^\s*([+\-]*\d+(\.\d+)*([Ee][+\-]*\d+)*)|(\?)|(\-)\s*$"
  p = re.search(p, quant)

  if not p:
    await ctx.message.add_reaction("❗")
    bot.print("Bad value given to inventory command: '%s'" % quant)
    return

  fp = bot.rootfp + "/inv/" + str(ctx.message.author.id) + ".json"
  if not os.path.exists(fp):
    open(fp, "a+").close()

  with open(fp, "r+") as data:
    data.seek(0)
    if not data.read():
      data.write("{\n\n}")
      data.truncate()

  inv = json_load(fp, bot.print)
  item = item.lower() if item is not None else None

  if quant == "?":
    if item is None:
      out = "```json\n{}\n```".format(json_dumps(inv))

      if len(out) > 2000:
        out = out[:-10] + "\n...\n}```"

      m = await ctx.send(out)
      return await del_or_pin(ctx.message, m, 10.0)

    inum = inv.get(item, 0)

  elif quant == "-":
    inv.pop(item, None)

    with open(fp, "w") as data:
      json_dump(inv, data)

  else:
    if ctx.guild.get_member(eval(quant)):
      id = ctx.guild.get_member(eval(quant)).id
      fp = bot.rootfp + "/inv/" + str(id) + ".json"

      if not os.path.exists(fp):
        open(fp, "a+").close()

      with open(fp, "r+") as data:
        data.seek(0)
        if not data.read():
          data.write("{\n\n}")
          data.truncate()

      inv = json_load(fp, bot.print)
      out = "```json\n{}\n```".format(json_dumps(inv))

      if len(out) > 2000:
        out = out[:-10] + "\n...\n}```"

      m = await ctx.send(out)
      return await del_or_pin(ctx.message, m, 10.0)

    elif item is None:
      m = await ctx.send("`item is a required argument that is missing.`")
      return await del_or_pin(ctx, m, 10.0)

    else:
      inum = eval(quant)
      if float(inum).is_integer:
        inum = int(inum)
      inv[item] = inv.get(item, 0) + inum

    with open(fp, "w") as data:
      json_dump(inv, data)

  inum = inv.get(item, 0)
  if inum == 0 and item == None:
    fmt = "{0.display_name} has nothing."
    m = await ctx.send(fmt.format(ctx.message.author))
  else:
    fmt = "{0.display_name} has {1} '{2}'"
    m = await ctx.send(fmt.format(ctx.message.author, inum, item))
  await del_or_pin(ctx.message, m, 10.0)


async def inventory_cmd(ctx, *args):
  kw = {"event": None, "id": ctx.message.author.id,
        "quant": 0, "item": ""}

  if len(args) == 0:
    kw["event"] = "show"

  elif args[0] == "?":
    kw["event"] = "show"

    if len(args) >= 2:
      if args[1].isdecimal() and ctx.guild.get_member(int(args[1])):
        kw["id"] = int(args[1])

        if len(args) >= 3:
          kw["item"] = " ".join(args[2:])

      else:
        kw["item"] = " ".join(args[1:])

  elif args[0] == "-":
    kw["event"] = "del"

    if len(args) >= 2:
      if args[1].isdecimal() and ctx.guild.get_member(int(args[1])):
        kw["id"] = int(args[1])

        if len(args) >= 3:
          kw["item"] = " ".join(args[2:])

      else:
        kw["item"] = " ".join(args[1:])

  elif re.search(r"^\s*[+\-]*\d+(\.\d+)*([Ee]\d+(\.\d+)*)*\s*$", args[0]):
    kw["event"] = "add"
    kw["quant"] = eval(args[0])

    if len(args) >= 2:
      kw["item"] = " ".join(args[1:])

  else:
    try:
      await ctx.message.add_reaction("❗")
      await asyncio.sleep(bot.timeout) if bot.timeout else None
      await ctx.message.delete() if bot.timeout else None
    except Exception as e:
      bot.print(e)
    return

  args = bot.inv(**kw)
  if args is False:
    try:
      await ctx.message.add_reaction("❗")
      await asyncio.sleep(bot.timeout) if bot.timeout else None
      await ctx.message.delete() if bot.timeout else None
    except Exception as e:
      bot.print(e)
    return

  if args[4]:
    fmt = "{0.display_name} has {1} '{2}'"
    args = ctx.message.author, args[3], args[4]

  else:
    fmt = "```json\n//Inventory for {0.display_name}\n{1}```"
    args = ctx.message.author, json_dumps(args[0])

  msg = await ctx.send(fmt.format(*args))
  await del_or_pin(ctx.message, msg, 20.0)

  await asyncio.sleep(bot.timeout) if bot.timeout else None
  try:
    await ctx.message.delete() if bot.timeout else None
  except Exception:
    pass


@bot.command(aliases=["die", "d", "D"])
async def dice(ctx, *, die: int=20):
  msg = await throw_die(ctx.message.channel, die)
  await del_or_pin(ctx.message, msg, 20.0)

  await asyncio.sleep(bot.timeout) if bot.timeout else None

  try:
    await ctx.message.delete() if bot.timeout else None
  except Exception:
    pass


@bot.command()
async def refresh(self, ctx):
  try:
    self.config = json_load(self.rootfp, self.print)
    self._wlist = self.config["wlist"]
    self._blist = self.config["blist"]
    self.timeout = self.config["delete_timeout"]

    game = discord.Game(self.config["status"])
    await self.change_presence(status=discord.Status.online, activity=game)

  except Exception as e:
    await ctx.message.add_reaction("❗")
    self.print(e)
  else:
    await ctx.message.add_reaction("🔁")

  await asyncio.sleep(self.timeout) if self.timeout else None

  try:
    await ctx.message.delete() if self.timeout else None
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
    fp = os.path.dirname(os.path.realpath(__file__)) + "/config.json"
  else:
    fp = " ".join(sys.argv[1:])

  logger = initlog(json_load(fp, Client.print))
  bot()
