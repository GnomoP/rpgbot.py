#!/usr/bin/env python3.6

import sys
import json
import logging


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


def initlog(json: dict):
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
