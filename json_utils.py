#!/usr/bin/env python3.6

import sys
import json


def json_dump(obj, fp):
  return json.dump(obj, fp, sort_keys=True, indent=2)


def json_dumps(obj):
  return json.dumps(obj, sort_keys=True, indent=2)


def json_load(fp, fprint=print):
  try:
    # Load configurations from filepath
    with open(fp) as f:
      json_dict = json.load(f)

  except IOError as e:
    fprint(e, file=sys.stderr)
    return {}

  except Exception as e:
    raise e

  else:
    json_dict.pop("opt", None)
    return json_dict
