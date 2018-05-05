#!/usr/bin/env python3.6

import os
import sys
import json
from datetime import datetime
from json_utils import json_load, json_dump, json_dumps


root = os.path.dirname(os.path.realpath(__file__))


class Inventory:
  def __init__(self, config_fp):
    self.root = os.path.dirname(os.path.realpath(__file__))

    if not os.path.isfile(config_fp):
      self.create_config(config_fp)

    self.cfg = self.json_load(config_fp)

  def __call__(self, event, id, quant=0, item=None):
    fp = self.root + "/inv/" + str(id) + ".json"
    if not os.path.isfile(fp):
      self.create_inventory(id)

    inv = self.json_load(fp)

    if item is not None and self.cfg["lowercase"]:
      item = item.lower()

    if event == "add":
      if item is None:
        item = "gold"

      inv[item] = inv.get(item, 0) + quant
      return inv, event, id, quant, item, self.update_inventory(id, inv)

    elif event == "del":
      if item is None:
        inv = {}
      else:
        quant = inv.pop(item, 0)

      return inv, event, id, quant, item, self.update_inventory(id, inv)

    elif event == "show":
      if item is None:
        return inv, event, id, quant, item, self.show_inventory(inv=inv)
      else:
        return inv, event, id, quant, item, inv.get(item, 0)

    else:
      return False

  def print(self, *args, **kwargs):
    time = datetime.now().strftime("[%T]")
    print(time, *args, **kwargs)

  def json_load(self, fp):
    return json_load(fp, self.print)

  def create_config(self, fp):
    """Creates a configuration file in JSON at the given filepath."""
    try:
      with open(fp, "w+") as f:
        json_dump({
          "lowercase": True,
          "max": -1
        }, f)

    except IOError as e:
      self.print(e)
      return False

    except Exception as e:
      raise e

    else:
      return True

  def create_inventory(self, id):
    """Creates an inventory file in JSON with an empty dictionary"""
    return self.update_inventory(id, {})

  def show_inventory(self, id=None, fp=None, inv=None):
    """Dumps an inventory file in JSON."""
    if id and not fp:
      fp = self.root + "/inv/" + str(id) + ".json"

    if not inv:
      inv = self.load_json(fp)

    return json_dumps(inv)

  def update_inventory(self, id, inv):
    """Updates an inventory file in JSON with the given dictionary."""
    fp = self.root + "/inv/" + str(id) + ".json"

    try:
      with open(fp, "w+") as f:
        json_dump(inv, f)

    except IOError as e:
      self.print(e)
      return False

    except Exception as e:
      raise e

    else:
      return True


if __name__ == "__main__":
  config_fp = os.path.dirname(os.path.realpath(__file__)) + "/inv/config.json"
  inventory = Inventory(config_fp)
