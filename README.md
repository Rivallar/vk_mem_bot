# vk_mem_bot
:laughing: A memes-bot for VKontakte social network.:smile:

### Description

Simple bot for social network VKontakte.
It collects posts from pinned publics, filters only the freshest ones and sends them to a user **at one click**!<br>

### Functionality

You can:

- get posts from all your publics at once
- get posts from a single public
- list your groups
- add/delete groups from your list
- list all available commands
- get button menu

Almost everything can be done via button menu.
The only two commands you really need to type are: **"кнопки"** to get button menu and **"\+groupname"** to add a new group to your list.
There is also full list of commands in the code.

> :warning:WARNING:warning:: it works only with posts with images, so posts with videos will be skipped. 
There are also some simple advertisement filters: no reposts and posts with big description are allowed.
And it sends each post only ones (except those pinned at the wall of a public).

### How to run:

`python3 vkbottle_bot.py`<br>
You need python3 with vkbottle module installed, your bot and app tokens and vkontakte public with all neccessary bot settings.
