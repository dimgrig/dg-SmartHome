#from secure import NAME, TOKEN, TOPIC
import os
NAME = os.environ.get('NAME', None)
TOKEN = os.environ.get('TOKEN', None)
TOPIC = os.environ.get('TOPIC', None)
URL_STR = os.environ.get('URL_STR', None)

import paho.mqtt.client as mqtt #pip install paho-mqtt

from queue import Queue

import cherrypy
import logging
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Dispatcher
import time
import threading
import urllib.parse as urlparse

TOPIC_STATUS = 0
text_ON = "Включить"
text_OFF = "Выключить"
reply_ON = "Включено"
reply_OFF = "Выключено"
reset = "Перезагрузка"

#https://apps.timwhitlock.info/emoji/tables/unicode
icon_ON=u'\U00002705'    #2705
icon_OFF=u'\U0000274C'  #274C

chat_ids = [199220133, 537459034]

bot = telegram.Bot(token=TOKEN, base_url='api.telegram.org/bot') #base_url='dg-telegram-bot-2.herokuapp.com/bot')

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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
url = urlparse.urlparse(URL_STR)

# Connect
mqttc.username_pw_set(url.username, url.password)
mqttc.connect(url.hostname, url.port)
#mqttc.connect_async(url.hostname, url.port)

# Start subscribe, with QoS level 0
mqttc.subscribe(TOPIC)

def send_KB_():
    icon = icon_ON if TOPIC_STATUS else icon_OFF
    not_icon = icon_OFF if TOPIC_STATUS else icon_ON
    text = text_OFF if TOPIC_STATUS else text_ON
    reply = reply_ON if TOPIC_STATUS else reply_OFF
    #print(icon, not_icon, text)
    custom_keyboard = [['РЕЗЕРВ', 'Cвет в спальне  ' + icon ],
                        [reset, text + "  " + not_icon]] 
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)
    for chat_id in chat_ids:
        bot.send_message(chat_id=chat_id, text=reply + " " + icon, reply_markup=reply_markup)
         


class SimpleWebsite(object):
    @cherrypy.expose
    def index(self):
        return """<H1>Welcome!</H1>"""


class BotComm(object):
    exposed = True

    def __init__(self, TOKEN, NAME):
        super(BotComm, self).__init__()
        self.TOKEN = TOKEN
        self.NAME=NAME
        self.bot = telegram.Bot(self.TOKEN)
        try:
            self.bot.setWebhook("https://{}.herokuapp.com/{}".format(self.NAME, self.TOKEN))
        except:
            raise RuntimeError("Failed to set the webhook")

        self.update_queue = Queue()
        self.dp = Dispatcher(self.bot, self.update_queue)

        self.dp.add_handler(CommandHandler("start", self._start))
        self.dp.add_handler(MessageHandler(Filters.text, self._handler))
        self.dp.add_error_handler(self._error)

    @cherrypy.tools.json_in()
    def POST(self, *args, **kwargs):
        update = cherrypy.request.json
        update = telegram.Update.de_json(update, self.bot)
        self.dp.process_update(update)

    def _error(self, error):
        cherrypy.log("Error occurred - {}".format(error))

    def _start(self, bot, update):
        update.effective_message.reply_text("Hi!")

    def _handler(self, bot, update):
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
      elif reset in update.message.text:
        #os.execv(__file__, sys.argv)
        update.message.reply_text(text="Перезагружаем")
        os.execl(sys.executable, 'python', __file__)        
      else:
        update.message.reply_text(text=update.message.text)

    
class ExcThread(threading.Thread):
    """LogThread should always e used in preference to threading.Thread.

    The interface provided by LogThread is identical to that of threading.Thread,
    however, if an exception occurs in the thread the error will be logged
    (using logging.exception) rather than printed to stderr.

    This is important in daemon style applications where stderr is redirected
    to /dev/null.

    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._real_run = self.run
        self.run = self._wrap_run

    def _wrap_run(self):
        try:
            self._real_run()
        except:
            print("CATCHED EXCEPTION")


if __name__ == "__main__":

    # Port is given by Heroku
    PORT = os.environ.get('PORT', '5000')

    # Set up the cherrypy configuration
    cherrypy.config.update({'server.socket_host': '0.0.0.0', })
    cherrypy.config.update({'server.socket_port': int(PORT), })
    cherrypy.tree.mount(SimpleWebsite(), "/")
    cherrypy.tree.mount(BotComm(TOKEN, NAME),
                        "/{}".format(TOKEN),
                        {'/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}})

    print('START ... ')
    #thread1 = threading.Thread(target=mqttc.loop_start())
    thread1 = ExcThread(target=mqttc.loop_start())
    thread1.start()
    print('MIDDLE ... ')
    #thread2 = threading.Thread(target=cherrypy.engine.start()) #  updater.idle()
    thread2 = ExcThread(target=cherrypy.engine.start()) #  updater.idle()
    thread2.start()
    print('END ... ')
    
