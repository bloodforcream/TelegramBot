import telebot
from telebot import types
import requests
from lxml import html
import datetime
from flask import Flask, request
import os
import time
from datetime import date
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime as datetime1

conn = sqlite3.connect("telebot.db", check_same_thread=False)
# conn.row_factory = sqlite3.Row
cursor = conn.cursor()

bot_token = '690634445:AAHtLz6-ussl5VYgKzgFvQJOYoFx1XGLNMM'

bot = telebot.TeleBot(token=bot_token)

server = Flask(__name__)

timenow = datetime.datetime.now()
cur_min = str(timenow).split()[1].split('.')[0].split(':')[1]

now = datetime.datetime.now()

markup_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
btn_get_info = types.KeyboardButton('Узнать дату выхода следующей серии')
btn_notifications = types.KeyboardButton('Получать оповещение о новых сериях')
btn_my_subs = types.KeyboardButton('Мои подписки')
btn_del_sub = types.KeyboardButton('Удалить подписку')
markup_menu.add(btn_get_info, btn_notifications, btn_my_subs, btn_del_sub)


def my_job(title_and_id):
    notification = 'Вышла новая серия {}'.format(title_and_id[1])
    bot.send_message(title_and_id[0], notification)


def get_next_episodes(list_of_all_episodes):
    for index, i in enumerate(list_of_all_episodes):
        if len(i) > 5:
            if len(i.split('.')) >= 3:
                if i.split('.')[2] > str(timenow).split()[0].split('-')[0]:
                    search_result = list_of_all_episodes[index:]
                    return search_result
                if i.split('.')[2] == str(timenow).split()[0].split('-')[0]:
                    if i.split('.')[1] > str(timenow).split()[0].split('-')[1]:
                        search_result = list_of_all_episodes[index:]
                        return search_result
                    if i.split('.')[1] == str(timenow).split()[0].split('-')[1]:
                        if i.split('.')[0] >= str(timenow).split()[0].split('-')[2]:
                            search_result = list_of_all_episodes[index:]
                            return search_result


def scheduler(dateEpi, name_title, user_id):
    date_of_episs = dateEpi
    title_and_id = [name_title, user_id]
    years = ''
    monthss = ''
    days = ''
    for i in date_of_episs:
        years += i.split('.')[2] + ', '
        if i.split('.')[1][0] == '0':
            monthss += i.split('.')[1].split('0')[-1] + ', '
        else:
            monthss += i.split('.')[1] + ', '
        if i.split('.')[0][0] == '0':
            days += i.split('.')[0].split('0')[-1] + ', '
        else:
            days += i.split('.')[0] + ', '
    sched = BackgroundScheduler()
    sched.add_job(my_job, 'cron', year=years[:-2], month=monthss[:-2], day=days[:-2], hour='12', args=[title_and_id])

    sched.start()


def get_info(search):
    r = requests.get('https://myshows.me/search/?q={}'.format(search))
    result = r.text
    result = result.split()
    for i in result:
        if '.me/view/' in i:
            link = i.split('"')[1]
            r = requests.get(link)
            r = html.fromstring(r.text)
            episodes = r.xpath('/html/body/div[1]/div/div/main/form/div/div/div/ul/li/label/a/span[1]/text()')[::-1]
            return episodes


def next_episode(list_of_episodes):
    if list_of_episodes is None:
        return list_of_episodes
    for i in list_of_episodes:
        if len(i.split('.')) >= 3:
            if i.split('.')[2] > str(timenow).split()[0].split('-')[0]:
                search_result = i
                return search_result
            if i.split('.')[2] == str(timenow).split()[0].split('-')[0]:
                if i.split('.')[1] > str(timenow).split()[0].split('-')[1]:
                    search_result = i
                    return search_result
                if i.split('.')[1] == str(timenow).split()[0].split('-')[1]:
                    if i.split('.')[0] >= str(timenow).split()[0].split('-')[2]:
                        search_result = i
                        return search_result


def days_till_next_epi(date_release):
    date_release = date_release.split('.')[::-1]
    now = str(datetime.datetime.now()).split()[0].split('-')
    d1 = date(int(date_release[0]), int(date_release[1]), int(date_release[2]))
    d0 = date(int(now[0]), int(now[1]), int(now[2]))
    delta = d1 - d0
    return delta


def seconds_in_total(days_till_next_episode):
    cur_time = str(datetime.datetime.now()).split()[1].split('.')[0].split(':')
    a = datetime.time(12, 00, 00)
    b = datetime.time(int(cur_time[0]), int(cur_time[1]), int(cur_time[2]))
    dateTimeA = datetime.datetime.combine(datetime.date.today(), a)
    dateTimeB = datetime.datetime.combine(datetime.date.today(), b)
    dateTimeDifference = dateTimeA - dateTimeB
    dateTimeDifferenceInSeconds = dateTimeDifference.total_seconds()
    seconds_till_next_episode = int(days_till_next_episode.total_seconds()) + int(dateTimeDifferenceInSeconds)
    return seconds_till_next_episode


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 'Welcome, {}'.format(message.from_user.first_name), reply_markup=markup_menu)


@bot.message_handler(content_types=['text'])
def notifications(message):
    if '/оповещения' in message.text:
        user_message = str(message.text)
        user_message = user_message.split('/оповещения ')[1]
        sql = "SELECT * FROM serials WHERE chat_id=? AND title=?"
        cursor.execute(sql, [(message.chat.id), (user_message.strip())])
        if cursor.fetchone():
            cursor.fetchone()
            bot.send_message(message.chat.id, 'Данный сериал уже добавлен')
            bot.send_photo(message.chat.id, 'https://i.redd.it/k2kldlnmg7y11.png')
            return
        if next_episode(get_info(user_message.strip())) is None:
            bot.send_message(message.chat.id, 'Не верное название сериала')
            bot.send_photo(message.chat.id, 'https://i.redd.it/k2kldlnmg7y11.png')
            return
        cortege = [(message.chat.id, user_message.strip(), next_episode(get_info(user_message.strip())))]
        cursor.executemany("INSERT INTO serials VALUES (?,?,?)", cortege)
        conn.commit()
        bot.send_message(message.chat.id, 'Данный сериал успешно добавлен')
        bot.send_photo(message.chat.id,
                       'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSVFUfiBgY-k2gm20B7ncewV2QW6gONab5yK4JpAySxSNkB5O_Q')
        scheduler(get_next_episodes(get_info(user_message.strip())), user_message.strip(), message.chat.id)
        return
        # USERS[message.from_user.id] = message.text.split('/оповещения')[-1]
        # users_next_episode_date = next_episode(get_info(USERS[message.from_user.id]))
        # if users_next_episode_date is None:
        #     bot.send_message(message.chat.id,
        #                      'Либо сериал уже закончился, либо следующая серия не анонсированна, либо {} не существует.'.format(
        #                          message.text.split('/оповещения')[-1]))
        #     bot.send_photo(message.chat.id, 'https://cdn.frankerfacez.com/emoticon/341836/4')
        #     return
        # bot.send_message(message.chat.id, 'Оповещение о выходе новой серии придет в полдень в день релиза.')
        # time.sleep(seconds_in_total(days_till_next_epi(users_next_episode_date)))
        # bot.send_message(message.chat.id, 'Вышла новая серия{}.'.format(USERS[message.from_user.id]))
        # return
    if '/удалить подписку' in message.text:
        user_message = str(message.text)
        user_message = user_message.split('/удалить подписку ')[1]
        sql = "DELETE FROM serials WHERE chat_id=? AND title=?"
        cursor.execute(sql, [(message.chat.id), (user_message.strip())])
        conn.commit()
        bot.send_message(message.chat.id, f'Сериал {user_message.strip()} удален из подписок')
        return
    if message.text == 'Получать оповещение о новых сериях':
        bot.reply_to(message, '/оповещения <название сериала>')
        return
    if message.text == 'Удалить подписку':
        bot.reply_to(message, '/удалить подписку <название сериала>')
        return
    if message.text == 'Узнать дату выхода следующей серии':
        bot.reply_to(message, 'Введите название')
        return
    if message.text == 'Мои подписки':
        sql_request = "SELECT * FROM serials WHERE chat_id=?"
        cursor.execute(sql_request, [(message.chat.id)])
        list_of_subs = cursor.fetchall()
        if len(list_of_subs) < 1:
            bot.send_message(message.chat.id, 'Нет активных подписок')
            return
        for subscription in list_of_subs:
            sub_info = str(subscription[1]).capitalize() + ', ' + 'Некст серия: {}'.format(str(subscription[2]))
            bot.send_message(message.chat.id, sub_info)
            sub_info = ''
        return
    search_result_to_show = next_episode(get_info(message.text))
    if (get_info(message.text)) is None:
        bot.send_message(message.chat.id, 'По данному запросу ничего не найдено')
        return
    if search_result_to_show:
        bot.send_message(message.chat.id, 'Следующая серия {}'.format(search_result_to_show))
    else:
        bot.send_message(message.chat.id, 'Следующая серия не анонсированна или сериал закончился')
        bot.send_photo(message.chat.id, 'https://cdn.frankerfacez.com/emoticon/341836/4')


@server.route('/' + bot_token, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@server.route("/")
def webbhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://sleepy-beach-82257.herokuapp.com/' + bot_token)
    return "!", 200


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
