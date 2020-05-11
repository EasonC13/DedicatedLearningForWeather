import configparser
import logging
from os import listdir
from os.path import isfile, join
import time
import datetime
import random
import json

from flask import Flask, request
import telegram
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import requests
import pymongo


class keyboard_maker:  # dict to obj
    def __init__(self, dictobj):
        for key, value in dictobj.items():
            setattr(self, key, value)


# static path
# path = "/home/eason/Python/Test/Pictures/"
static_path = "../pictures_weather/"

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initial TOKEN config
config = configparser.ConfigParser()
config.read('../config/config.ini')

# Initial Flask app
app = Flask(__name__)

# Initial bot by Telegram access token
bot = telegram.Bot(token=(config['TELEGRAM']['ACCESS_TOKEN_FOR_Weather']))

# Initial mongodb
mongo_database = pymongo.MongoClient("mongodb://localhost:27017/")
account_DB = mongo_database["UserData"]
account_collection = account_DB["Account"]


# flask route
@app.route('/hook', methods=['POST'])
def webhook_handler():
    """Set route /hook with POST method will trigger this method."""
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
    return 'ok'


# function
def get_photo_files():
    global static_path
    return [file for file in listdir(static_path) if isfile(join(static_path, file))]


def get_rate_inline_board():
    out = [str(float(i / 10)) for i in range(10, 50, 10)]
    return [out]


# core function
def send_typing_action(update):
    """Show the bot is typing to user."""
    bot.send_chat_action(chat_id=update.message.chat.id, action=telegram.ChatAction.TYPING)


account_dict = {}
def user_setup(update, chat_id):
    account = account_dict.get(chat_id)
    if account is None:
        datetime_dt = datetime.datetime.today()
        time_delta = datetime.timedelta(days=-1)
        new_dt = datetime_dt + time_delta
        account_dict[chat_id] = {"chat_id": chat_id, "points": 0, "last gamble time": new_dt.strftime("%Y/%m/%d")}
        update.message.reply_text("歡迎新成員加入平台\n目前擁有0點", reply_markup=KeyBoards.default)
        update.message.reply_text("如須重設，請輸入 /start", reply_markup=KeyBoards.default)
    else:
        update.message.reply_text("歡迎回來{}~\nLv.{}\n目前擁有{}點\n再{}Exp升等".format(account_dict[chat_id]['chat_id'], 999, account_dict[chat_id]["points"], random.randint(1, 999)),reply_markup=KeyBoards.default)

    # account = account_collection.find_one({"chat_id": chat_id})
    # if account is None:
    #     datetime_dt = datetime.datetime.today()
    #     time_delta = datetime.timedelta(days=-1)
    #     new_dt = datetime_dt + time_delta
    #
    #     account_collection.insert_one({"chat_id": chat_id, "points": 0, "last gamble time": new_dt.strftime("%Y/%m/%d")})
    #     update.message.reply_text("歡迎新成員加入平台\n目前擁有0點", reply_markup=KeyBoards.default)
    # else:
    #     update.message.reply_text("歡迎回來{}~\nLv.{}\n目前擁有{}點\n再{}Exp升等".format('Name', 999, account["points"], random.randint(1, 999)), reply_markup=KeyBoards.default)




        # TODO BUG?
        # ranking = list(account_collection.find().sort("points")).index(account)
        # update.message.reply_text("目前擁有{}點\n全體排名{}".format(account["points"], ranking), reply_markup=KeyBoards.default)


def send_photo(chat_id, photos, path=static_path):
    for photo in photos:
        bot.send_photo(chat_id, photo=open(path + photo, 'rb'))


def make_gamble_money_interface(select_data):
    temp = []
    for i in [10, 25, 50, 100]:
        select_data.update({'stage':4, 'money':i})#{, 'stage': 4}
        tmps = "/GO " + json.dumps(select_data)
        temp.append(InlineKeyboardButton(str(i), callback_data=tmps))
    return InlineKeyboardMarkup( 
        [temp]
    )


def make_gamble_date_select_interface(select_data):
    pass


def make_index_interface(select_data):
    temp = []
    for i in range(ord('A'), ord('G')+1):
        select_data.update({'ans': chr(i), 'stage': 3})
        temp.append("/GO " + json.dumps(select_data))
        
    if select_data['type'] == 'HT':
        pass    # TODO
    elif select_data['type'] == 'AQ':
        return InlineKeyboardMarkup([
                [InlineKeyboardButton("良好", callback_data=temp[0])],
                [InlineKeyboardButton("普通", callback_data=temp[1])],
                [InlineKeyboardButton("對敏感族群不健康", callback_data=temp[2])],
                [InlineKeyboardButton("對所有族群不健康", callback_data=temp[3])],
                [InlineKeyboardButton("非常不健康與危害", callback_data=temp[4])]
        ])
    elif select_data['type']  == 'ST':
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("10°C以下", callback_data=temp[0])],
            [InlineKeyboardButton("11~15°C", callback_data=temp[1])],
            [InlineKeyboardButton("16~20°C", callback_data=temp[2])],
            [InlineKeyboardButton("21~25°C", callback_data=temp[3])],
            [InlineKeyboardButton("26~30°C", callback_data=temp[4])],
            [InlineKeyboardButton("31~35°C", callback_data=temp[5])],
            [InlineKeyboardButton("36°C(含)以上", callback_data=temp[6])]
        ])


# Prepare Constant
ProcessingQueue = []

welcome_message = """
    歡迎使用「做你的天氣先知」
    請使用下方鍵盤來使用平台
"""

help_message = """
    根據想要的功能，點擊下方的按鈕
    感到疑惑的話，可以點擊"天氣懶人包"試試看
"""

# 大鍵盤 Button setting
location_keyboard = telegram.KeyboardButton(text="傳送定位資訊", request_location=True)
cancel_keyboard = telegram.KeyboardButton(text="取消")

# 大鍵盤 main keyboard setting
KeyBoards = {"default": ReplyKeyboardMarkup([['我的個人資訊'],['📡今日天氣'], ['開始下注'], ['歷史下注紀錄'], ['🏆查看排行榜'], ['📖推薦文章'],['開始Demo']]),#['快速獲得結果']
    "request_location": ReplyKeyboardMarkup([[location_keyboard], [cancel_keyboard]])}
KeyBoards = keyboard_maker(KeyBoards)

# 大鍵盤 photo setting
Photos = {"cloud": ['(體驗天氣3)雲種1.PNG', "(體驗天氣3)雲種2.PNG", "(體驗天氣3)雲種3.PNG"],
    "air_quality": ["(體驗天氣2)空氣品質.PNG", "(天氣賭盤2)空品等級.PNG"], "all": get_photo_files()}
Photos = keyboard_maker(Photos)

# special keyboard
rate_board = ReplyKeyboardMarkup(get_rate_inline_board(), resize_keyboard=True, one_time_keyboard=True, selective=True)



# common text decoder & processor
def reply_processor(update):
    text = update.message.text
    reply_text = update.message.reply_text
    chat_id = update.message.chat.id

    if text == '📡今日天氣':
        reply_text("請提供您的定位資訊：\n(建議開啟GPS以取得最佳體驗)", reply_markup=KeyBoards.request_location)

    elif text == '開始下注':
        # TODO
        # account = account_collection.find_one({"chat_id": chat_id})
        order = gamble_order_dict.get(chat_id)
        if order is None:
            temp = '/GO ' + json.dumps({'type': 'HT', 'stage': 1})
            temp2 = '/GO ' + json.dumps({'type': 'AQ', 'stage': 1})
            temp3 = '/GO ' + json.dumps({'type': 'ST', 'stage': 1})
            temp4 = '/GO ' + json.dumps({'type': 'cancel', 'stage': 1})
            gamble_main_keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("單日最高溫", callback_data=temp)],
                     [InlineKeyboardButton("空氣品質", callback_data=temp2)],
                     [InlineKeyboardButton("體感溫度", callback_data=temp3)],
                     [InlineKeyboardButton("取消", callback_data=temp4)]
                ]
            )

            reply_text("下注吧~請問要賭什麼呢?\n(開發階段，賭的為24小時之後的值)", reply_markup=gamble_main_keyboard)
        else:
            print("a-2")
            reply_text("每日只能下注一次~", reply_markup=KeyBoards.default)

    elif text == '歷史下注紀錄':
        reply_text("此功能尚未開放", reply_markup=KeyBoards.default)

    elif text == '我的個人資訊':
        user_setup(update, chat_id)

    elif text == '🏆查看排行榜':
        reply_text("https://demo.ntnu.best/?p=62", reply_markup=KeyBoards.default)

    elif text == '📖推薦文章':
        send_photo(chat_id, Photos.all)

    elif text == "開始Demo":
        time.sleep(5)
        reply_text("早安~", reply_markup=KeyBoards.default)
        reply_text("請提供您的定位資訊：\n(建議開啟GPS以取得最佳體驗)", reply_markup=KeyBoards.request_location)

    elif text == "快速獲得結果":
        # TODO handle by worker
        # account = account_collection.find_one({"chat_id": chat_id})
        print('c')
        account = account_dict[chat_id]
        print('c-d')
        if random.random() < 0.7:   # TODO quiz data base
            print('c-1')
            decode_item = {'HT': '單日最高溫', 'AQ':'空氣品質', 'ST':'體感溫度'}
            
            
            reply_text(
                '已贏得賭博~\n 項目:{}\n日期:{}\n選項:{}\n下注金額:{}'.format(
                    decode_item[gamble_order_dict[chat_id]['type']],
                    gamble_order_dict[chat_id]['date'],
                    gamble_order_dict[chat_id]['ans'],
                    gamble_order_dict[chat_id]['money']
                ),
                reply_markup=KeyBoards.default
            )

            account['points'] += 100
            # account_collection.update_one(
            #     {"chat_id": chat_id},
            #     {"$set": {"points": int(account['points']) + 100}})
        else:
            print('c-2')
            reply_text('賭輸 www.google.com.tw', reply_markup=KeyBoards.default)
        del account_dict[chat_id]
    
    elif text == "取消":
        reply_text("已取消", reply_markup=KeyBoards.default)
    else:
        reply_text("聽不懂QQ", reply_markup=KeyBoards.default)

    # debug
    logger.info('user %s (%s) send %s', chat_id, update.message.chat.first_name + " " + update.message.chat.last_name, text)

    return True


# command handler
def start_handler(bot, update):
    # db process
    user_setup(update, update.message.chat.id)
    update.message.reply_text(welcome_message, reply_markup=KeyBoards.default)


def help_handler(bot, update):
    update.message.reply_text(help_message, reply_markup=KeyBoards.default)

    
def reset_handler(bot, update):
    account_dict.clear()
    gamble_order_dict.clear()
    update.message.reply_text("已重置", reply_markup=KeyBoards.default)
    

# core handler
def reply_handler(bot, update):
    """Reply message."""
    chat_id = update.message.chat.id
    if chat_id not in ProcessingQueue:
        ProcessingQueue.append(chat_id)
        send_typing_action(update)
        reply_processor(update)
        ProcessingQueue.remove(chat_id)


# location & weather info handler
apiData = []
def location_handler(bot, update):
    update.message.reply_text('請稍後，正在尋找您附近的天氣狀況')
    send_typing_action(update)

    # Receive weather info --------------------------------------------------------------------------------
    # Find the nearest observation station
    user_lon = update['message']['location']['longitude']
    user_lat = update['message']['location']['latitude']

    url = 'https://opendata.cwb.gov.tw/fileapi/v1/opendataapi/O-A0003-001?Authorization=CWB-78790FE9-7153-44A8-ABEE-6764D108C6F1&format=json'  # temp, humd
    res = requests.get(url)
    res_dict = res.json()
    n = len(res_dict['cwbopendata']['location'])  # 44 observation stations

    # calculate distance between user and a station
    def cal_distance(i, user_lon, user_lat):
        lat = float(res_dict['cwbopendata']['location'][i]['lat'])
        lon = float(res_dict['cwbopendata']['location'][i]['lon'])
        dis = (user_lat - lat) ** 2 + (user_lon - lon) ** 2
        return dis

    # going through the 44 stations and find out which is the nearest one
    record = 0
    temp = cal_distance(0, user_lon, user_lat)
    for i in range(1, n):
        result = cal_distance(i, user_lon, user_lat)
        if (result < temp):
            temp = result
            record = i

    ##Test
    apiData.append(res_dict)
    ##Test

    temper = res_dict['cwbopendata']['location'][record]['weatherElement'][3]['elementValue']['value']
    humd = int(float(res_dict['cwbopendata']['location'][record]['weatherElement'][4]['elementValue']['value']) * 100)
    uv = res_dict['cwbopendata']['location'][record]['weatherElement'][13]['elementValue']['value']

    loc = res_dict['cwbopendata']['location'][record]['locationName']
    time = res_dict['cwbopendata']['location'][record]['time']['obsTime']

    # prepare user data
    user_id = update['message']['chat']['id']
    return_data = {'user': user_id, 'TEMP': temper, 'HUMD': humd, 'UVI': uv}

    # get AQI
    url2 = "https://opendata.epa.gov.tw/api/v1/AQI?%24skip=0&%24top=1000&%24format=json"
    res2 = requests.get(url2)
    aqi_lis = res2.json()

    def cal_dis(lon, user_lon, lat, user_lat):
        dis = (user_lat - lat) ** 2 + (user_lon - lon) ** 2
        return dis

    temp = cal_dis(float(aqi_lis[0]['Longitude']), user_lon, float(aqi_lis[0]['Latitude']), user_lat)
    record = 0
    for i in range(1, len(aqi_lis)):
        lon = float(aqi_lis[i]['Longitude'])
        lat = float(aqi_lis[i]['Latitude'])
        if (cal_dis(lon, user_lon, lat, user_lat) < temp):
            temp = cal_dis(lon, user_lon, lat, user_lat)
            record = i

    aqi = aqi_lis[record]['AQI']
    aqi_status = aqi_lis[record]['Status']

    # prepare user data
    return_data = {'user': user_id, 'TEMP': temper, 'HUMD': humd, 'UVI': uv, 'AQI': aqi, 'Status': aqi_status,
                   'Loc': loc, 'Time': time}

    # --------------------------------------------------------------------------------------------------

    update.message.reply_text(
        '現在氣溫{}度 / 濕度 : {}% \n紫外線指數 : {} \nAQI指數 : {} ({}) \n\n(測站資訊:{}，{})'.format(return_data['TEMP'],
                                                                                    return_data['HUMD'],
                                                                                    return_data['UVI'],
                                                                                    return_data['AQI'],
                                                                                    return_data['Status'],
                                                                                    return_data['Loc'],
                                                                                    return_data['Time']),
        reply_markup=KeyBoards.default)


gamble_order_dict = {}
def callback_handler_gamble_option(bot, update):
    print('b')
    query = update.callback_query
    chat_id = query.message.chat_id
    data = json.loads(query.data.replace("/GO ", ""))
    print('b-d')
    if data['stage'] == 4:
        print('b-4')
        # write DB
        data.update({'date':datetime.datetime.now().date()})
        print(data)
        gamble_order_dict[chat_id] = data
        print('b-4-d')
        query.edit_message_text(text="下注成功")

    elif data['stage'] == 3:
        print('b-3')
        query.edit_message_text(
            text="選擇籌碼",
            reply_markup=make_gamble_money_interface(data)
        )
    elif data['stage'] == 2:
        print('b-2')
        query.edit_message_text(text="選擇籌碼", reply_markup=make_gamble_money_interface(data))
        # query.edit_message_text(
        #     text="選擇日期",
        #     reply_markup=make_gamble_date_select_interface(data)
        # )
    elif data['stage'] == 1:
        print('b-1')
        if "cancel" in query.data:
            query.edit_message_text(text="已取消")
            return True
        query.edit_message_text(
            text="選指標",
            reply_markup=make_index_interface(data)
        )

    else:
        logger.info('Unhandle InnerButton Routing Trigger by gamble callback')
    #     tmp = query.data.split(",")
    #     query.edit_message_text(text="選擇了{}項目，賭了{}點".format(tmp[0], tmp[1]), reply_markup=InlineKeyboardMarkup(
    #         [[InlineKeyboardButton("快速查看結果（測試用）", callback_data='/gamble_reslut win,{}'.format(tmp[1]))]]))


# def callback_handler_gamble_reslut(bot, update):
#     query = update.callback_query
#     if "win" in query.data:
#         query.edit_message_text(text="已贏得賭博~")
#         #         print("b1")
#         account = account_collection.find_one({"chat_id": query.message.chat_id})
#         account_collection.update_one({"chat_id": query.message.chat_id},
#                                       {"$set": {"points": int(account['points']) + int(query.data.split(",")[1])}})
#     #         print("b3")
#     else:
#         pass


def error_handler(bot, update, error):
    """Log Errors caused by Updates."""
    logger.error('Update "%s" caused error "%s"', update, error)  # update.message.reply_text('對不起，系統錯誤，請關閉後重新使用')


# New a dispatcher for bot
dispatcher = Dispatcher(bot, None)

# Add handler for handling message, there are many kinds of message. For this handler, it particular handle text
# message.
dispatcher.add_error_handler(error_handler)


dispatcher.add_handler(CommandHandler('start', start_handler))
dispatcher.add_handler(CommandHandler('help', help_handler))
dispatcher.add_handler(CommandHandler('reset', reset_handler))

dispatcher.add_handler(MessageHandler(Filters.location, location_handler))
dispatcher.add_handler(MessageHandler(Filters.text, reply_handler))

dispatcher.add_handler(CallbackQueryHandler(callback_handler_gamble_option, pattern="/GO"))
# dispatcher.add_handler(CallbackQueryHandler(callback_handler_gamble_reslut, pattern="/gamble_reslut"))

if __name__ == "__main__":
    app.run(port=5003, threaded=True)

# https://api.telegram.org/bot{TOKEN}/setWebhook?url=https://gcp4-1.easonc.tw/hook