import requests
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import tokens
import shelve
import json

vk_session = vk_api.VkApi(token=tokens.bot_key)
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()
upload = vk_api.VkUpload(vk)


def get_fresh_group_posts(group_name):
    """Gets definite amount of posts for a group. Filters fresh ones and prepares them for sending."""

    # Getting posts and their ids
    url = f'https://api.vk.com/method/wall.get?domain={group_name}&count=30&access_token={tokens.app_token}&v=5.131'
    req = requests.get(url)
    src = req.json()
    posts = src['response']['items']
    new_posts_ids = set([post['id'] for post in posts])

    # Searching for fresh posts, updating list of post ids
    groups = shelve.open('groups.conf', flag='c')
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
                post['attachments'] != None,
                len(post['text']) < 100
                    ]):
                    attachments_info = []
                    for ind, item in enumerate(post['attachments']):
                        if item['type'] == 'photo':
                            attachments_info.append(f'photo{item["photo"]["owner_id"]}_{item["photo"]["id"]}')
                    if attachments_info:
                        post_content.append({'text': post['text'], 'attachments_info': attachments_info})
    groups.close()
    return post_content


def send_message(user_id, text, keyboard=None, carousel=None):
    """Sends information to a user"""

    message_dict = {'user_id': user_id, 'message': text, 'random_id': 0}
    if keyboard:
        message_dict['keyboard'] = keyboard.get_keyboard()
    if carousel:
        message_dict['template'] = carousel
    vk_session.method('messages.send', message_dict)


def send_group_posts(group_name, posts, user_id):
    send_message(user_id, f'Посты из группы {group_name}:')
    for post in posts:
        vk.messages.send(user_id=user_id, random_id=0, message=post['text'], attachment=post['attachments_info'])
    send_message(user_id, f'Посты из {group_name} закончились')

def send_group_names(user_id, group_names, text):
    """Sends a list of group names as buttons (3 per line)"""

    groups_keyboard = VkKeyboard(inline=True)
    for ind, name in enumerate(group_names):
        groups_keyboard.add_button(f'{name}', VkKeyboardColor.SECONDARY)
        if (ind + 1) % 3 == 0 and (ind + 1) != len(group_names):
            groups_keyboard.add_line()
    send_message(user_id, text, groups_keyboard)


def main():
    command_list = '''Список доступных команд:
    
    кнопки - вывести кнопки с командами
    команды - вывести все доступные команды
    мои группы - вывести список групп с мемами
    мемы - выслать все свежие мемы всех групп сразу
    group_name - свежие мемы одной группы
    +group_name - добавить группу в список
    -group_name - убрать группу из списка'''

    with shelve.open('groups.conf') as groups:
        ram_group_names = list(groups.keys())

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            # if event.from_chat:
            msg = event.text.lower()
            user_id = event.user_id

            # BOT commands

            if msg == 'тест':
                send_message(user_id, 'привет')

            elif msg == 'кнопки':
                keyboard = VkKeyboard()
                keyboard.add_button('Мемы', VkKeyboardColor.POSITIVE)
                keyboard.add_button('Команды', VkKeyboardColor.PRIMARY)
                keyboard.add_button('Мои группы', VkKeyboardColor.SECONDARY)
                send_message(user_id, 'Высылаю кнопки', keyboard=keyboard)

            elif msg == 'команды':
                send_message(user_id, command_list)

            elif msg == 'мои группы':
                group_names = ram_group_names[:]
                info = 'Список групп:'
                while group_names:
                    send_group_names(user_id, group_names[:9], info)
                    group_names = group_names[9:]
                    info = 'Ещё группы:'

            elif msg == 'мемы':
                send_message(user_id, 'Высылаю посты всех групп сразу')
                for group_name in ram_group_names:
                    try:
                        posts = get_fresh_group_posts(group_name)
                        send_group_posts(group_name, posts, user_id)
                    except Exception:
                        send_message(user_id, f'Что-то не так с группой {group_name}')
                send_message(user_id, 'На этот раз всё :)')

            elif msg in ram_group_names:
                posts = get_fresh_group_posts(msg)
                send_group_posts(msg, posts, user_id)

            elif msg.startswith('+'):
                group_name = msg.lstrip('+')
                with shelve.open('groups.conf', flag='c') as groups:
                    groups[group_name] = set()
                    ram_group_names.append(group_name)
                send_message(user_id, f'Группа: {group_name} добавлена в список. Убедитесь что она действительна!')

            elif msg.startswith('-'):
                group_name = msg.lstrip('-')
                with shelve.open('groups.conf', flag='c') as groups:
                    try:
                        del groups[group_name]
                        send_message(user_id,
                                     f'Группа: {group_name} удалена из списка.')
                        ram_group_names.remove(group_name)
                    except KeyError:
                        send_message(user_id, f'Группы {group_name} нет в списке!')

            elif msg == 'стена':
                attach = 'video-30022666_456240349'
                vk.messages.send(user_id=user_id, random_id=0, message='тестим стену',
                                 attachment=attach)

            elif msg == 'карусель':
                element = {
        "title": "Title",
        "description": "Description",
        "action": {
                "type": "open_link",
                "link": "https://vk.com"
        },
        "photo_id": "-30022666_457338521",
        "buttons": [{
                "action": {
                        "type": "text",
                        "label": "Label"
                }
        }]
}
                carousel = {
    "type": "carousel",
    "elements": [element, element, element]
        }

                send_message(user_id, 'тестим карусель', carousel=json.dumps(carousel))

            else:
                send_message(user_id, 'Не понял! Напиши "команды" чтобы увидеть список всех команд.')


if __name__ == '__main__':
    main()
