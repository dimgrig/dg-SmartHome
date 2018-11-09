from secure import NAME, TOKEN, TOPIC

import os
import paho.mqtt.client as mqtt #pip install paho-mqtt
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import time
import threading
import urllib.parse as urlparse


TOPIC_STATUS = 0
text_ON = "Включить"
text_OFF = "Выключить"
reply_ON = "Включено"
reply_OFF = "Выключено"

#https://apps.timwhitlock.info/emoji/tables/unicode
icon_ON=u'\U00002705'    #2705
icon_OFF=u'\U0000274C'  #274C

chat_ids = [199220133, ]

bot = telegram.Bot(token=TOKEN, base_url='dg-telegram-bot-2.herokuapp.com/bot')

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')

def send_KB_():
    icon = icon_ON if TOPIC_STATUS else icon_OFF
    not_icon = icon_OFF if TOPIC_STATUS else icon_ON
    text = text_OFF if TOPIC_STATUS else text_ON
    reply = reply_ON if TOPIC_STATUS else reply_OFF
    #print(icon, not_icon, text)
    custom_keyboard = [['РЕЗЕРВ', 'Cвет в спальне  ' + icon ],
                        ['РЕЗЕРВ', text + "  " + not_icon]] 
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)
    for chat_id in chat_ids:
        bot.send_message(chat_id=chat_id, text=reply + " " + icon, reply_markup=reply_markup)
   
"""def send_KB(bot, update):
    icon = icon_ON if TOPIC_STATUS else icon_OFF
    not_icon = icon_OFF if TOPIC_STATUS else icon_ON
    text = text_OFF if TOPIC_STATUS else text_ON
    #print(icon, not_icon, text)
    custom_keyboard = [['РЕЗЕРВ', 'Cвет в спальне  ' + icon ], ###
                        ['РЕЗЕРВ', text + "  " + not_icon]] ### 
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)
    update.message.reply_text(text=".", reply_markup=reply_markup)
"""
def handler(bot, update):
  global TOPIC
  global TOPIC_STATUS
  print(update.message.chat_id, update.message.text)
  if update.message.text == 'kb' or update.message.text == 'keyboard':
    #send_KB(bot, update)
    send_KB_()
  elif text_ON in update.message.text:
    mqttc.publish(TOPIC, "ON", 0, True)
    #TOPIC_STATUS = 1
    #send_KB(bot, update)
  elif text_OFF in update.message.text:
    mqttc.publish(TOPIC, "OFF", 0, True)
    #TOPIC_STATUS = 0
    #send_KB(bot, update)
  else:
    update.message.reply_text(text=update.message.text)


# Define event callbacks
def on_connect(client, userdata, flags, rc):
    print("on_connect rc: " + str(rc))

def on_message(client, obj, msg):
    global TOPIC_STATUS
    print("on_message " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    if msg.topic == TOPIC:
        if msg.payload == b'ON':
            TOPIC_STATUS = 1
            send_KB_()
        elif msg.payload == b'OFF':
            TOPIC_STATUS = 0
            send_KB_()
    print(TOPIC_STATUS)    
    
def on_publish(client, obj, mid):
    print("on_publish mid: " + str(mid))

def on_subscribe(client, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(client, obj, level, string):
    print(string)

mqttc = mqtt.Client()
# Assign event callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe

# Uncomment to enable debug messages
#mqttc.on_log = on_log

# Parse CLOUDMQTT_URL (or fallback to localhost)
url_str = 'mqtt://esp12:esp12123qwe@m23.cloudmqtt.com:12042'
url = urlparse.urlparse(url_str)

# Connect
mqttc.username_pw_set(url.username, url.password)
mqttc.connect(url.hostname, url.port)

# Start subscribe, with QoS level 0
mqttc.subscribe(TOPIC)

if __name__ == "__main__":
    # Port is given by Heroku
    

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, handler))

    # Start the Bot
    updater.start_polling()

    # Start the webhook
    updater.start_webhook(listen="0.0.0.0",
                          port=int(os.environ.get('PORT', '8443')),
                          url_path=TOKEN)
    updater.bot.setWebhook("https://{}.herokuapp.com/{}".format(NAME, TOKEN))


    print('Listening ... ')    

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.  
        
    print('START ... ')
    thread1 = threading.Thread(target=mqttc.loop_start())    
    thread1.start()
    print('MIDDLE ... ')
    thread2 = threading.Thread(target=updater.idle())
    thread2.start()
    print('END ... ')
