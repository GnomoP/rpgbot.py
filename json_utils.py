#!/usr/bin/env python3.6

import sys
import json


def json_dump(obj, fp):
  return json.dump(obj, fp, sort_keys=True, indent=2)


def json_dumps(obj):
  return json.dumps(obj, sort_keys=True, indent=2)


def json_load(fp, fprint=print):
  """Returns a dictionary from a JSON file in the given filepath.

  File at the given filepath is opened as read-only. An
  optional `opt` parameter, containing any metadata, will
  be removed from the returned dictionary.

  If an `IOError` is caught, the error is logged to the `stderr`
  stream with the `fprint` function, which defaults to the print
  builtin, and an empty dictionary is returned instead.

  Any other errors will be raised.
  """
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
