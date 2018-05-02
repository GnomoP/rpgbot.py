#!/usr/bin/env python3.6

import os
import sys
import json
from datetime import datetime
from json_utils import json_load


class Inventory:
  def __init__(self, config_fp):
    if not os.path.isfile(config_fp):
      self.create_config(config_fp)
    self.cfg = self.json_load(config_fp)

  def __call__(self, event, quant=0, item=None):
    print("self: ", self)
    print("event:", event)
    print("quant:", quant)
    print("item: ", item)

  def print(self, *args, **kwargs):
    time = datetime.now().strftime("[%T]")
    print(time, *args, **kwargs)

  def json_load(self, fp):
    return json_load(fp, self.print)

  def create_config(self, fp):
    """Creates a configuration file in JSON at the given filepath."""
    try:
      with open(fp, "w+") as f:
        json_dict = {
          "lowercase": True,
          "max": -1
        }

        json.dump(json_dict, f, sort_keys=True, indent=2)

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
