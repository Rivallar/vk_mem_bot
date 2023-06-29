import shelve
import time

import tokens
import json
from vkbottle import Keyboard, KeyboardButtonColor, Text
from vkbottle.bot import Bot, Message
import logging
import asyncio


logging.disable(logging.DEBUG)

command_list = '''Список доступных команд:

кнопки - вывести кнопки с командами
команды - вывести все доступные команды
мои группы - вывести список групп с мемами
мемы - выслать все свежие мемы всех групп сразу
group_name - свежие мемы одной группы
+group_name - добавить группу в список
-group_name - убрать группу из списка'''

#reading a list of added groups and id`s of previously sent posts.
with shelve.open('groups.conf') as groups:
    ram_group_names = list(groups.keys())


bot = Bot(tokens.bot_key)


async def get_fresh_group_posts(message, group_name):
    """Getting fresh posts from groups wall. Taking only those with photos and not seen yet.
    Preparing them as message attachment"""

    request = await bot.api.wall.get(domain=group_name, count=30, access_token=tokens.app_token, v='5.131', ssl=False)
    request_str = request.json()
    request_dict = json.loads(request_str)
    posts = request_dict['items']

    new_posts_ids = set([post['id'] for post in posts])

    # Searching for fresh posts, updating list of post ids
    with shelve.open('groups.conf', flag='c') as groups:
        if group_name not in list(groups.keys()):
            groups[group_name] = new_posts_ids
            fresh_posts = new_posts_ids
        else:
            fresh_posts = new_posts_ids - groups[group_name]
            group_name_list = list(groups[group_name] | new_posts_ids)
            group_name_list.sort()
            group_name_list = group_name_list[-40:]
            groups[group_name] = set(group_name_list)

    # Filtering for only photos and forming post_content
    post_content = []
    for post in posts:
        if post['id'] in fresh_posts:
            if all([
                'attachments' in post,
                post['attachments'] is not None,
                len(post['text']) < 200
            ]):
                try:
                    attachments_info = []
                    for ind, item in enumerate(post['attachments']):
                        if item['type'] == 'photo':
                            attachments_info.append(f'photo{item["photo"]["owner_id"]}_{item["photo"]["id"]}')
                    if attachments_info:
                        post_content.append({'text': post['text'], 'attachments_info': attachments_info})
                except Exception:
                    await message.answer(f'Проблема с постом {post["id"]}:')
                    continue
    return post_content


async def send_group_posts(message, posts, group_name):
    """Sends previously prepared posts to a user."""

    await message.answer(f'Посты из группы {group_name}:')
    for post in posts:
        await asyncio.create_task(message.answer(post['text'], attachment=post['attachments_info']))
    await message.answer(f'Посты из {group_name} закончились')


async def send_group_names(message, group_names, text, to_delete=False):
    """Sends a list of group names as buttons (3 per line). White buttons to view posts of a group.
    Red buttons to delete a group from a list."""

    groups_keyboard = Keyboard(inline=True)
    if not to_delete:
        color = KeyboardButtonColor.SECONDARY
        prefix = ''
    else:
        color = KeyboardButtonColor.NEGATIVE
        prefix = '-'
    for ind, name in enumerate(group_names):
        groups_keyboard.add(Text(f'{prefix}{name}'), color=color)
        if (ind + 1) % 3 == 0 and (ind + 1) != len(group_names):
            groups_keyboard.row()
    await message.answer(text, keyboard=groups_keyboard)



@bot.on.message(text="Ещё")
@bot.on.private_message(payload={'menu': 'menu'})
async def menu_handler(message: Message):
    """Interactive menu. Replaces standard buttons to additional ones."""

    keyboard = (
        Keyboard()
        .add(Text('Команды'), color=KeyboardButtonColor.PRIMARY)
        .add(Text('Удалить группу'), color=KeyboardButtonColor.NEGATIVE)
        .add(Text('Назад', {'menu': 'main'}), color=KeyboardButtonColor.SECONDARY)

    )
    await message.answer('Высылаю доп. меню', keyboard=keyboard)

@bot.on.message(text="Назад")
@bot.on.private_message(payload={'menu': 'main'})
async def back_to_main(message):
    """To return to main menu."""

    keyboard = (
        Keyboard()
        .add(Text('Мемы'), color=KeyboardButtonColor.POSITIVE)
        .add(Text('Мои группы'), color=KeyboardButtonColor.PRIMARY)
        .add(Text('Ещё', {'menu': 'menu'}), color=KeyboardButtonColor.SECONDARY)
    )
    await message.answer('Возвращаю в главное меню', keyboard=keyboard)



@bot.on.message()
async def message_handler(message: Message) -> str:
    """Bot handling users commands."""

    #send a list of available commands
    if message.text.lower() == 'команды':
        await message.answer(command_list)

    #send buttons menu
    elif message.text.lower() == 'кнопки':
        keyboard = (
            Keyboard()
            .add(Text('Мемы'), color=KeyboardButtonColor.POSITIVE)
            .add(Text('Мои группы'), color=KeyboardButtonColor.PRIMARY)
            .add(Text('Ещё', {'menu': 'menu'}), color=KeyboardButtonColor.SECONDARY)
        )
        await message.answer('Высылаю кнопки', keyboard=keyboard)

    #send a list of remembered groups as buttons
    elif message.text.lower() == 'мои группы':
        group_names = ram_group_names[:]
        info = 'Список групп:'
        while group_names:
            await send_group_names(message, group_names[:9], info)
            group_names = group_names[9:]
            info = 'Ещё группы:'

    #send posts of all groups at once
    # elif message.text.lower() == 'мемы':
    #     await message.answer("Высылаю посты всех групп сразу")
    #     for group_name in ram_group_names:
    #         try:
    #             posts = await get_fresh_group_posts(message, group_name)
    #             await send_group_posts(message, posts, group_name)
    #         except Exception:
    #             await message.answer(f'Непонятная ошибка при отсылке мемов группы {group_name}')
    #     await message.answer("На этот раз всё :)")

    elif message.text.lower() == 'мемы':
        await message.answer("Высылаю посты всех групп сразу")
        tasks = []
        for group_name in ram_group_names:
            tasks.append(asyncio.create_task(get_fresh_group_posts(message, group_name)))
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            await send_group_posts(message, result, ram_group_names[i])
        await message.answer("На этот раз всё :)")


    #adds/removes a group from a list
    elif message.text.startswith('+'):
        group_name = message.text.lstrip('+')
        with shelve.open('groups.conf', flag='c') as groups:
            groups[group_name] = set()
            ram_group_names.append(group_name)
        await message.answer(f'Группа: {group_name} добавлена в список. Убедитесь что она действительна!')

    elif message.text.startswith('-'):
        group_name = message.text.lstrip('-')
        with shelve.open('groups.conf', flag='c') as groups:
            try:
                del groups[group_name]
                ram_group_names.remove(group_name)
                await message.answer(f'Группа: {group_name} удалена из списка.')
            except KeyError:
                await message.answer(f'Группы {group_name} нет в списке!')

    #sends posts from one group requested
    elif message.text.lower() in ram_group_names:
        group_name = message.text
        posts = await get_fresh_group_posts(message, group_name)
        await send_group_posts(message, posts, group_name)

    #sends a list of groups as red buttons to delete a group by pushing its button
    elif message.text.lower() == 'удалить группу':
        group_names = ram_group_names[:]
        info = 'Список групп:'
        while group_names:
            await send_group_names(message, group_names[:9], info, to_delete=True)
            group_names = group_names[9:]
            info = 'Ещё группы:'

    else:
        #for unknown commands
        await message.answer('Не понял. Напиши "команды", чтобы увидеть список доступных команд.')



bot.run_forever()

