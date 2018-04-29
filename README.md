Documentação em Português (BR) disponível em [README_PT-BR.md](https://github.com/GnomoP/blob/master/README_PT-BR.md) (TODO).

# dumb-bot

Discord bot written with the [discord.py](https://github.com/Rapptz/discord.py) wrapper (rewrite branch) made by [Rapptz](https://github.com/Rapptz).

# Requirements

+ Python v3.6 (tested on Ubuntu 16.04 LTS)
+ discord.py (rewrite branch) and it's dependencies
  + Installing with pip: `python3.6 -m pip install -U --user git+https://github.com/Rapptz/discord.py.git@rewrite`

# Usage

Change the parameters in `config.json`, using `config-example.json` as a skeleton if needed, to suit your needs as follows:

+ `logging_level`: Set to one of the five, in order to specify the verbose level for logging: `CRITICAL`, `ERROR`, `WARNING`, `INFO`, or `DEBUG`. Defaults to `WARNING` if unspecified.
+ `opt`: Parameters for the logging file. Leave this alone if you don't know what you're doing.
+ `delete_timeout`: Specify how many seconds to wait before deleting a command's message. Set to 0 to not delete anything.
+ `args` and `kwargs`: Arguments given to the wrapper. Leave this alone if you don't know what you're doing.
+ `prefix` and `token` are self explanatory.
+ `announcements`: Specify the ID of a channel for event announcements. Leave it empty to not announce any events.
+ `status`: Set the status message to show under the bot.
+ `wlist` and `blist` are, respectively, the whitelist and the blacklist of users, guilds and channels the bot will interpret messages from. Paramaters should be given as snowflake IDs (the number sequence you get when you select "Copy ID" after right-clicking their icon or name). The former takes precedence over the latter.

Any functionality not affected by the settings is programmable through the source code itself.

# Acknowledgements

This bot was written for personal use, over at a specific Discord guild. Any and all updates archived here are done in regards to it's function at that guild, and as such, any pull requests requesting features lacking utility at that guild will be ignored and/or closed.