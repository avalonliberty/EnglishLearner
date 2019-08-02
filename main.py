from flask import Flask, request, abort
import pymongo
import json
import re
import inflect
from datetime import date
from datetime import datetime
from EngDict import EngDictionary

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

app = Flask(__name__)

# access the user config
with open("config", "r") as fileLink:
    configContent = fileLink.read().split()
    for line in configContent:
        if line.split("=")[0] == "token":
            token = line.split("=")[1]
        elif line.split("=")[0] == "secret":
            secret = line.split("=")[1]
        elif line.split("=")[0] == "password":
            password = line.split("=")[1]

db_ip = "172.19.0.3"
db_port = "27017"
selected_days = [1, 2, 3, 5, 8, 13, 21]
source_github = 'https://github.com/avalonliberty/EnglishLearner'

# show examples
def show_examples(word, user_id):
    user_dict = EngDictionary()
    user_dict.fit(word)
    content = user_dict.look_up()
    message = ""
    for word in content["content"]:
        for sentence in word["example"]:
            sentence += "\n\n"
            message += sentence
    line_bot_api.push_message(user_id, TextSendMessage(text = message))

# give instructions
def display_instructions(user_id):
    message = "There are serveral operations that you could take\n"
    message += "1. 'start service' for turning on auto push\n"
    message += "2. 'stop service' for turning off auto push\n"
    message += "3. 'add {vocabulary}' for adding a new vocabulary\n"
    message += "4. 'check {vocabulary}' for looking up the vocabulary\n"
    message += "5. 'example {vocabulary}' for showing example sentences\n\n"
    message += "If you need further instruction, please refet to " + source_github
    line_bot_api.push_message(user_id, TextSendMessage(text = message))

# define the operation start service
def start_service(user_id):
    exist = user_exist(user_id)
    if exist:
        client = pymongo.MongoClient("mongodb://" + db_ip + ":" + db_port)
        users = client["users"]
        user_info = users["info"]
        user_info.update_one({"user_id" : user_id},
                             {"$set" : {"activation" : 1}})
        client.close()
    else:
        add_user(user_id)
    message = "Sucessfully start service"
    line_bot_api.push_message(user_id, TextSendMessage(text = message))

# define the operation stop service
def stop_service(user_id):
    exist = user_exist(user_id)
    if exist:
        client = pymongo.MongoClient("mongodb://" + db_ip + ":" + db_port)
        users = client["users"]
        user_info = users["info"]
        user_info.update_one({"user_id" : user_id},
                             {"$set" : {"activation" : 0}})
    else:
        add_user(user_id, activation = 0)
    message = "Sucessfully stop service"
    line_bot_api.push_message(user_id, TextSendMessage(text = message))

# check if users exist in the user database
def user_exist(user_id):
    client = pymongo.MongoClient("mongodb://" + db_ip + ":" + db_port)
    users = client["users"]
    user_info = users["info"]
    exist = bool(user_info.find({"user_id" : user_id}).count())
    client.close()
    return exist

#add new users into the user database
def add_user(user_id, activation = 1):
    client = pymongo.MongoClient("mongodb://" + db_ip + ":" + db_port)
    users = client["users"]
    user_info = users["info"]
    user_information = {"user_id" : user_id,
                        "activation" : activation,
                        "join_date" : str(date.today())}
    user_info.insert_one(user_information)
    client.close()

#define dictionary display
def display_word(content, user_id):
    greetings = f'You are reviewing the word {content["word"]!r}'
    line_bot_api.push_message(user_id, TextSendMessage(text = greetings))
    transformer = inflect.engine()
    for index, description in enumerate(content["content"]):
        nth = transformer.ordinal(index + 1)
        message = f'{nth} : '
        message += f'{description["def"]["pos"]!r}\n'
        message += f'Meaning : {description["def"]["definition"]!r}'
        line_bot_api.push_message(user_id, TextSendMessage(text = message))

#define the action for 'add'
def add_vocabulary(word, user_id, timestamp):
    client = pymongo.MongoClient("mongodb://" + db_ip + ":" + db_port)
    voc_db = client["EngDict"]
    user_db = voc_db[user_id]
    duplicate = user_db.find({"word" : word}).count()
    if duplicate:
        reply = f'{word!r} was in the review list!!'
    else:
        user_dict = EngDictionary()
        user_dict.fit(word)
        content = user_dict.look_up()
        if isinstance(content, dict):
            content["timestamp"] = timestamp
            user_db.insert_one(content)
            reply = f'Insertion complete!!'
        elif isinstance(content, str):
            reply = content
    client.close()
    line_bot_api.push_message(user_id, TextSendMessage(text = reply))

#define the action for 'check'
def check_vocabulary(word, user_id):
    user_dict = EngDictionary()
    user_dict.fit(word)
    content = user_dict.look_up()
    if isinstance(content, dict):
        display_word(content, user_id)
    elif isinstance(content, str):
        reply = content
        line_bot_api.push_message(user_id, TextSendMessage(text = reply))

def record_command(user_id, command, action, timestamp):
    client = pymongo.MongoClient("mongodb://" + db_ip + ":" + db_port)
    sysDB = client["sysInfo"]
    commandRecord = sysDB["commandRecord"]
    commandDict = {'user_id' : user_id,
                   'command' : command,
                   'action' : action,
                   'timestamp' : timestamp}
    commandRecord.insert_one(commandDict)
    client.close()

# Channel Access Token
line_bot_api = LineBotApi(token)
# Channel Secret
handler = WebhookHandler(secret)

#The endpoint for pushing daily words to users
@app.route("/dailyWord", methods = ["GET", "POST"])
def dailyWord():
    if request.args.get('password') == password:
        client = pymongo.MongoClient("mongodb://" + db_ip + ":" + db_port)
        user_db = client["users"]
        user_info = user_db["info"]
        voc_db = client["EngDict"]
        for user in user_info.find({"activation" : 1}):
            user_table = voc_db[user['user_id']]
            for word in user_table.find():
                insert_date = datetime.strptime(word["insert_date"], "%Y-%m-%d")
                day_in_db = (datetime.today() - insert_date).days + 1
                if day_in_db in selected_days:
                    display_word(word, user["user_id"])
    return ""

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['GET', 'POST'])
def callback():
    global user_id, timestamp
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    request_body = json.loads(body)
    timestamp = request_body["events"][0]["timestamp"]
    user_id = request_body["events"][0]["source"]["userId"]
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global user_id, timestamp
    #message = TextSendMessage(text=event.message.text)
    message = event.message.text.lower()
    rule = re.compile(r'(^add\s*\w*)|(^check\s*\w*)|(example\s*\w*)|(^review\s*current)|(^review\s*old)|(start service)|(stop service)')
    match = re.match(rule, message)
    if match:
        action = match.string.split()[0]
        if action == "add":
            word = match.string.split()[1]
            add_vocabulary(word, user_id, timestamp)
        elif action == "check":
            word = match.string.split()[1]
            check_vocabulary(word, user_id)
        elif action == "start":
            start_service(user_id)
        elif action == "stop":
            stop_service(user_id)
        elif action == "example":
            word = match.string.split()[1]
            show_examples(word, user_id)
        record_command(user_id, match.string, action, timestamp)
    else:
        message = "Unknown operations"
        line_bot_api.push_message(user_id, TextSendMessage(text = message))
        display_instructions(user_id)
    #line_bot_api.reply_message(event.reply_token, message)


import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
