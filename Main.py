# -*- coding: utf-8 -*-
import time
import requests
import json

API_VK = 'https://api.vk.com/method/'
CONFIG_PATH = 'config/configuration.json'
ERROR_TOO_MANY_REQUESTS = 6


# сделать запрос к API
def get_api_data(method, params):
    api_link = '{}{}'.format(API_VK, method)
    while True:
        response = requests.get(api_link, params=params)
        response.raise_for_status()
        response = response.json()
        print('-')
        if 'response' in response:
            return response['response']['items']
        else:
            error = response['error']['error_code']
            if error == ERROR_TOO_MANY_REQUESTS:
                time.sleep(0.4)
                continue
            else:
                return response

# получить id по имени пользователя
def users_search(user):
    settings = read_json_file(CONFIG_PATH)
    params = {
        'access_token': settings['access_token'],
        'v': settings['version'],
        'q': user
    }
    user_list = get_api_data('users.search', params)
    user_id = user_list[0]['id']
    return user_id

# получить группы
def get_groups(user_id, common_params):
    params = {
        'user_id': user_id,
        'count': 1000,
        'extended': 1,
        'fields': 'members_count'
        }
    params.update(common_params)
    groups = get_api_data('groups.get', params)
    return groups


# получить друзей
def get_user_friends(user_id):
    settings = read_json_file(CONFIG_PATH)
    params = {
        'access_token': settings['access_token'],
        'v': settings['version'],
        'user_id': user_id,
        'fields': 'name'
    }
    friends = get_api_data('friends.get', params)
     # выбираем только неудаленных друзей
    valid_friends = [fr for fr in friends if 'deactivated' not in fr]
    new_valid_friends = []
    for element in valid_friends:
        if element['is_closed'] == True:
            continue
        new_valid_friends.append(element)
    return new_valid_friends


def read_json_file(filename):
    with open(filename, encoding='utf-8') as data_file:
        data = json.load(data_file)
    return data


def write_json_data(filename, text):
    with open(filename, mode='w', encoding='utf-8') as file:
        file.write(text)

def execute(chunk_friends):
    settings = read_json_file(CONFIG_PATH)
    code = 'var friends_groups = [];' \
           f'var friends = {chunk_friends};' \
           'var i = 0;' \
           'while (i < friends.length) {' \
           '  friends_groups.push(API.groups.get({"user_id": friends[i], "extended": 0}));' \
           '  i = i + 1;' \
           '}' \
           'return friends_groups;'
    resp = requests.get('https://api.vk.com/method/execute', params={
        'access_token': settings['access_token'],
        'v': 5.103,
        'code': code,
    })
    a = resp.json()
    b = [x['items'] for x in a['response']]
    friend_groups_overall = set()
    for d in b:
        friend_groups_overall = friend_groups_overall.union(d)
    return friend_groups_overall


def main():

    # читаем настройки
    settings = read_json_file(CONFIG_PATH)

    params = {
        'access_token': settings['access_token'],
        'v': settings['version']
        }

    user = input('Введите имя или id пользователя в ВК для анализа: ')
    try:
        user_id = int(user)
    except:
        user_id = users_search(user)

    # получаем список друзей и групп пользователя
    friends = get_user_friends(user_id)
    groups = get_groups(user_id, params)
    my_groups_id = [gr['id'] for gr in groups]

    # готовим данные для работы с функцией execute
    friends_id = []
    for k in friends:
        id = k['id']
        friends_id.append(id)

    chunk_friends = []
    new_set = set()
    for i in range(len(friends_id)):
        chunk_friends.append(friends_id[i])
        if i%25 == 0:
            friend_groups = execute(chunk_friends)
            print('-')
            chunk_friends = []
            new_set.update(friend_groups)
        if i == (len(friends_id) - 1):
            friend_groups = execute(chunk_friends)
            new_set.update(friend_groups)

    # находим разность множеств между группами пользователя и группами друзей
    result_set = set(my_groups_id).difference(new_set)

    # преобразуем итог в список с id
    result_groups_ids = list(result_set)

    # для финального результата собираем список словарей с полями 'id', 'name', 'members_count'
    result_groups_json = []
    for gr in groups:
         if gr['id'] in result_groups_ids:
            result_groups_json.append({k: v for k, v in gr.items() if (k in ('id', 'name', 'members_count'))})
    for em in result_groups_json:
        em['gid'] = em.pop('id')

    # пишем json в файл
    write_json_data('groups.json', str(result_groups_json))
    print('Обработано успешно, результат сохранен в файле groups.json')




if __name__ == "__main__":
    main()

