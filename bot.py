#!/usr/bin/env python3.6

import re
import os
import sys
import time
import asyncio
import logging
import json as json_parser
from random import randrange
from datetime import datetime
from subprocess import Popen, PIPE
import discord
from discord import abc
from discord.ext import commands


rootdir = os.path.dirname(os.path.realpath(__file__))
config_json = "%s/config.json" % rootdir


def parse_configs():
  with open(config_json) as data:
    json = json_parser.load(data)
  return json


def initlog(json):
  logger = logging.getLogger("discord")

  try:
    logger.setLevel(eval("logging.%s" % json["logging_level"]))
  except Exception:
    logger.setLevel(logging.INFO)

  if "opt" in json:
    opt = json["opt"]
  else:
    opt = {"filename": "discord.log", "encoding": "utf-8", "mode": "w"}

  handler = logging.FileHandler(**opt)
  fmt = "%(asctime)s:%(name)s: %(message)s"
  handler.setFormatter(logging.Formatter(fmt))

  logger.addHandler(handler)
  return logger


def json_dump(obj, fp):
  return json_parser.dump(obj, fp, sort_keys=True, indent=2)


def json_dumps(obj):
  return json_parser.dumps(obj, sort_keys=True, indent=2)


class Client(commands.Bot):
  def __init__(self, config: list):
    args = config["args"]
    kwargs = config["kwargs"]
    prefix = config["prefix"]

    self._bot = not config["kwargs"]["self_bot"]
    self._token = config["token"]
    self._wlist = config["wlist"]
    self._blist = config["blist"]

    self.t = config["delete_timeout"]

    self.config = config
    self.paused = False

    super().__init__(prefix, *args, **kwargs)

    self.remove_command("help")
    self.add_command(self.dice)
    self.add_command(self.shutdown)
    self.add_command(self.refresh)
    self.add_command(self.restart)
    self.add_command(self.pause)
    self.add_command(self.purge)
    self.add_command(self.shell)
    self.add_command(self._eval)
    self.add_command(self._inventory)
    self.add_command(self._python)
    self.add_command(self._say)

  def __call__(self):
    Popen("clear", shell=True)
    time.sleep(1)

    self.print("Running bot now...")
    self.run(self._token, bot=self._bot)

  def print(self, *args, **kwargs):
    time = datetime.now().strftime("[%T]")
    print(time, *args, **kwargs)

  def trim_codeblocks(self, string):
    string = string[1:] if string.startswith("\n") else string
    string = string[3:-3] if string.startswith("```") else string
    string = string[1:-1] if string.startswith("`") else string

    string = string[8:] if string.startswith("python3") else string
    string = string[8:] if string.startswith("python2") else string
    string = string[7:] if string.startswith("python") else string
    string = string[5:] if string.startswith("bash") else string
    string = string[3:] if string.startswith("py") else string
    string = string[3:] if string.startswith("sh") else string
    return "\n" + string

  def check_msg(self, m):
    if m.type == discord.MessageType.default and (
        (
          isinstance(m.channel, discord.DMChannel) and
          m.channel.recipient.id not in self._blist["users"]
        ) or (
          isinstance(m.channel, discord.GroupChannel) and
          m.channel.id not in self._blist["channels"]
        ) or (
          isinstance(m.channel, abc.GuildChannel) and
          m.channel.id not in self._blist["channels"] and
          m.author.id not in self._blist["users"] and
          m.guild.id in self._wlist["guilds"]
        ) or (
          m.author.id in self._wlist["users"] or
          m.channel.id in self._wlist["channels"]
        )
      ):
      return True
    else:
      return False

  async def msgdiag_delpin(self, org_msg, message, time=10.0):
    # await ctx.message.add_reaction('✅')
    await message.add_reaction('📌')
    await message.add_reaction('❌')

    def check_1(react, user):
      a = user.id == org_msg.author.id
      b = str(react.emoji) in ('📌', '❌')
      c = react.message.id == message.id
      return a and b and c
    
    def check_2(react, user):
      a = user.id == org_msg.author.id
      b = str(react.emoji) == '📌'
      c = react.message.id == message.id
      return a and b and c
    
    try:
      react, user = await self.wait_for(
        "reaction_add", timeout=time, check=check_1)
    except asyncio.TimeoutError:
      try:
        await message.delete()
        await org_msg.delete()
      except Exception as e:
        pass
      return
    react = str(react.emoji)

    if react == '📌':
      react, user = await self.wait_for(
        "reaction_remove", check=check_2)
    elif react == '❌':
      pass
    else:
      await asyncio.sleep(time)    

    try:
      await message.delete()
      await org_msg.delete()
    except Exception as e:
      pass

  async def msgdiag_yesno(self, message, default: bool=False, time=10.0):
    await message.add_reaction('👍')
    await message.add_reaction('👎')

    def check(react, user):
      a = user.id == message.author.id
      b = str(react.emoji) in ('👍', '👎')
      c = react.message.id == message.id
      return a and b and c
    
    try:
      react, user = await self.wait_for(
        "reaction_add", timeout=time, check=check)
    except asyncio.TimeoutError:
      return default
    react = str(react.emoji)

    if react == '👍':
      return True
    else:
      return False

  async def throw_die(self, channel: abc.Messageable, die=int):
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

  async def on_connect(self):
    self.print("Connected to Discord...")
    await self.wait_until_ready()

    self.print("Logged in as %s" % self.user)
    self.print("Command prefix: '%s'" % self.command_prefix)

    game = discord.Game(self.config["status"])
    await self.change_presence(status=discord.Status.online, activity=game)

  async def on_message(self, m):
    if self.check_msg(m):
      await self.process_commands(m)
    
    if self.paused:
      return

    # Match die rolls for integers (D20, d-2, d 21, etc.)
    p = re.compile(r'^\s*[Dd][ +\-]*\d+\s*$')
    if p.match(m.clean_content):
      die = int(re.search(r'\d+', m.clean_content).group())
      msg = await self.throw_die(m.channel, die)
      await self.msgdiag_delpin(m, msg, 20.0)
    
    # Access, modify or delete the inventory
    p = re.compile(r'^\s*inv(entory)* .*\s*$')
    if p.match(m.clean_content):
      pass    

  async def on_message_delete(self, m):
    if m.author.id in self._wlist["users"] or m.author.id == self.user.id:
      return

    if m.clean_content and not self.paused:
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

      if not self.config["announcements"]:
        return

      # Log to announcements channel
      ann = self.get_channel(self.config["announcements"])
      await ann.send(fmt.format(m.author, content, date))

  async def on_member_join(self, member):
    if not self.paused:
      for role in member.guild.roles:
        if role.name.startswith("Plebeu"):
          break
      await member.add_roles(role, reason="Plébe")

      # Log to announcements channel
      if not self.config["announcements"]:
        return

      ann = self.get_channel(self.config["announcements"])
      await ann.send(
        "{0.mention} é um Plebeu. Siga as normas, *rusticus*.".format(member))

  async def on_command_error(self, ctx, e):
    if type(e).__name__ in ("CommandNotFound", "CheckFailure", "NotOwner"):
      return

    if type(e).__name__ in ("BadArgument", "MissingRequiredArgument"):
      await ctx.send("`%s`" % e)
      return

    if type(e).__name__ == "CommandInvokeError":
      if type(e.original).__name__ in ("HTTPException", "NotFound"):
        return

      if type(e.original).__name__ == ("ClientException", "Forbidden"):
        await ctx.send("`%s`" % e)
        return

    self.print(e)

  @commands.is_owner()
  @commands.command()
  async def shutdown(self, ctx):
    try:
      await ctx.message.add_reaction("👋")
    except Exception:
      pass

    await asyncio.sleep(self.t) if self.t else None

    try:
      await ctx.message.delete() if self.t else None
    except Exception:
      pass

    await self.logout()
    self.print("Logged out. Shutting down...")

  @commands.is_owner()
  @commands.command()
  async def restart(self, ctx):
    try:
      await ctx.message.add_reaction("👋")
    except Exception:
      pass

    await asyncio.sleep(self.t) if self.t else None

    try:
      await ctx.message.delete() if self.t else None
    except Exception:
      pass

    self.print("Restarting...")
    os.execl(sys.executable, sys.executable, *sys.argv)

  @commands.command()
  async def refresh(self, ctx):
    try:
      self.config = parse_configs()
      self._wlist = self.config["wlist"]
      self._blist = self.config["blist"]

      game = discord.Game(self.config["status"])
      await self.change_presence(status=discord.Status.online, activity=game)

    except Exception as e:
      await ctx.message.add_reaction("❗")
      self.print(e)
    else:
      await ctx.message.add_reaction("🔁")

    await asyncio.sleep(self.t) if self.t else None

    try:
      await ctx.message.delete() if self.t else None
    except Exception:
      pass

  # @commands.command(name="inv2")
  # async def _inventory(self, ctx, *args, **kwargs):
  # def inventory(event, player_id, quant, item):

  @commands.command(name="inventory", aliases=["inv"])
  async def _inventory(self, ctx, quant, *, item=None):
    p = r'^(\s*[+-]*\d+(\.\d+)*([Ee][+-]*\d+)*\s*)|(\?+)|(-+)$'
    p = re.search(p, quant)

    if not p:
      await ctx.message.add_reaction("❗")
      # print("Bad value given to inventory command: '%s'" % quant)
      self.print("Bad value given to inventory command: '%s'" % quant)
      return

    # inv_fp = "%s/inv/.json" % rootdir
    inv_fp = "%s/inv/%s.json" % (rootdir, ctx.message.author.id)
    if not os.path.exists(inv_fp):
      open(inv_fp, "a+").close()

    with open(inv_fp, "r+") as data:
      data.seek(0)
      if not data.read():
        data.write("{\n\n}")
        data.truncate()
      
      data.seek(0)
      inv_js = json_parser.load(data)

    item = item.lower() if item is not None else None
    if quant == "?":
      if item is None:
        out = "```json\n{}\n```".format(json_dumps(inv_js))
        if len(out) > 2000:
          out = out[:-10] + "\n...\n}```"
        m = await ctx.send(out)
        await self.msgdiag_delpin(ctx, m, 10.0)
        return
      
      inum = inv_js.get(item, 0)

    elif quant == "-":
      inv_js.pop(item, None)

      with open(inv_fp, "w") as data:
        json_dump(inv_js, data)

    else:
      if item is None:
        m = await ctx.send("`item is a required argument that is missing.`")
        await self.msgdiag_delpin(ctx, m, 10.0)
        return

      inum = eval(quant)
      if float(inum).is_integer:
        inum = int(inum)
      inv_js[item] = inv_js.get(item, 0) + inum

      with open(inv_fp, "w") as data:
        json_dump(inv_js, data)

    inum = inv_js.get(item, 0)
    # fmt = "Player has {0} '{1}'"
    fmt = "{0.display_name} has {1} '{2}'"
    # print(fmt.format(inum, item))
    m = await ctx.send(fmt.format(ctx.message.author, inum, item))
    await self.msgdiag_delpin(ctx, m, 10.0)

  @commands.command(aliases=["die", "d", "D"])
  async def dice(self, ctx, *, die: int=20):
    msg = await self.throw_die(ctx.message.channel, die)
    await self.msgdiag_delpin(ctx.message, msg, 20.0)

  @commands.command()
  async def pause(self, ctx):
    self.paused = not self.paused
    if self.paused:
      try:
        await ctx.message.add_reaction('⏸')
      except Exception as e:
        await ctx.message.add_reaction("❗")
        self.print(e)
    else:
      try:
        await ctx.message.add_reaction('⏩')
      except Exception as e:
        await ctx.message.add_reaction("❗")
        self.print(e)

    await asyncio.sleep(self.t) if self.t else None

    try:
      await ctx.message.delete() if self.t else None
    except Exception:
      pass

  @commands.command()
  async def purge(self, ctx, limit: int=100):
    try:
      deleted = len(await ctx.channel.purge(limit=limit + 1))
      await ctx.send("Deleted %s message(s)" % deleted, delete_after=10.0)
    except Exception as e:
      await ctx.send("An error occured. Refer to the log for more information")
      raise e

  @commands.is_owner()
  @commands.command()
  async def shell(self, ctx, *, script):
    try:
      await ctx.message.add_reaction('🐚')
    except Exception:
      pass

    script = self.trim_codeblocks(script)
    Popen(script, shell=True)

    try:
      await ctx.message.add_reaction('✅')
    except Exception:
      pass

  @commands.is_owner()
  @commands.command()
  async def send(self, ctx, *, filepath=__file__):
    if filepath.startswith("-/"):
      filepath.replace("-/", "~/Pictures")

  @commands.command(name="python2", aliases=["py2"])
  async def _python(self, ctx, *, pycode):
    pycode = self.trim_codeblocks(pycode)
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
      self.print(e)

  @commands.command(name="eval", aliases=["python", "py"])
  async def _eval(self, ctx, *, pycode):
    pycode = self.trim_codeblocks(pycode)
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
      self.print(e)

  @commands.is_owner()
  @commands.command(name="say")
  async def _say(self, ctx, *, message):
    self.print(message)

    try:
      await ctx.message.delete()
    except Exception:
      pass

    await ctx.send(message)

if __name__ == "__main__":
  config = parse_configs()
  logger = initlog(config)
  client = Client(config)

  client()
