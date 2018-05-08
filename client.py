#!./env/bin/python

import os
import sys
import time
import asyncio
from datetime import datetime
from subprocess import Popen
import discord
from discord import abc
from discord.ext import commands
from bot_utils import initlog
from json_utils import json_load


class Client(commands.Bot):
  def __init__(self, config_fp: str):
    self.config = json_load(config_fp, self.print)

    self._wlist = self.config["wlist"]
    self._blist = self.config["blist"]
    self.timeout = self.config["delete_timeout"]

    self.paused = False
    self.rootfp = os.path.dirname(os.path.realpath(__file__))

    args = self.config["args"]
    kwargs = self.config["kwargs"]
    prefix = self.config["prefix"]

    super().__init__(prefix, *args, **kwargs)
    self.remove_command("help")
    self.add_command(self.shutdown)
    self.add_command(self.restart)
    self.add_command(self.pause)
    self.add_command(self.purge)
    self.add_command(self.say)

  def __call__(self):
    Popen("clear", shell=True)
    time.sleep(1)

    self.print("Running bot now...")
    self.run(self.config["token"], bot=not self.config["kwargs"]["self_bot"])

  def print(self, *args, **kwargs):
    time = datetime.now().strftime("[%T]")
    print(time, *args, **kwargs)

  def check_msg(self, m):
    if m.type != discord.MessageType.default:
      return

    checks = [
      isinstance(m.channel, discord.DMChannel) and
      m.channel.recipient.id not in self._blist["users"],

      isinstance(m.channel, discord.GroupChannel) and
      m.channel.id not in self._blist["channels"],

      isinstance(m.channel, abc.GuildChannel) and
      m.channel.id not in self._blist["channels"] and
      m.author.id not in self._blist["users"] and
      m.guild.id in self._wlist["guilds"],

      m.author.id in self._wlist["users"] or
      m.channel.id in self._wlist["channels"]
    ]

    for check in checks:
      if check:
        return True

    return False

  async def on_message(self, m):
    if self.check_msg(m):
      await self.process_commands(m)

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

    await asyncio.sleep(self.timeout) if self.timeout else None

    try:
      await ctx.message.delete() if self.timeout else None
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

    await asyncio.sleep(self.timeout) if self.timeout else None

    try:
      await ctx.message.delete() if self.timeout else None
    except Exception:
      pass

    self.print("Restarting...")
    os.execl(sys.executable, sys.executable, *sys.argv)

  @commands.command()
  async def pause(self, ctx):
    self.paused = not self.paused

    if self.paused:
      try:
        await ctx.message.add_reaction('⏸')
      except Exception as e:
        self.print(e)

    else:
      try:
        await ctx.message.add_reaction('⏩')
      except Exception as e:
        self.print(e)

  @commands.is_owner()
  @commands.command()
  async def purge(self, ctx, limit: int=100):
    deleted = len(await ctx.channel.purge(limit=limit + 1))
    await ctx.send("Deleted %s message(s)" % deleted, delete_after=10.0)

  @commands.is_owner()
  @commands.command()
  async def say(self, ctx, *, message):
    self.print(message)

    try:
      await ctx.message.delete()
      await ctx.send(message)
    except Exception as e:
      self.print(e)


if __name__ == "__main__":
  if len(sys.argv) < 2:
    fp = os.path.dirname(os.path.realpath(__file__)) + "/inv/config.json"
  else:
    fp = " ".join(sys.argv[1:])

  logger = initlog(json_load(fp, Client.print))
  client = Client(fp)

  client()
