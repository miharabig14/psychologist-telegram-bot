import telebot
from telebot import types
import json
import logging
import sqlite3
import datetime
from dateutil import parser
from dateutil.parser._parser import ParserError


with open("data.json","r") as j: 
    bot_info =  json.loads(j.read()) #Json to dict 

FORMAT = f'%(asctime)s %(message)s'
logging.basicConfig(filename="log.log",
                    filemode='a',
                    format=FORMAT,
                    datefmt='%H:%M:%S'
)

db = sqlite3.connect("db.db", check_same_thread=False)
cur = db.cursor()
logging.debug("[DEBUG] Database has been connect")

cur.execute("""CREATE TABLE IF NOT EXISTS user(
    chat_id INTEGER NOT NULL UNIQUE,
    user_name VARCHAR(32) NULL,
    first_name VARCHAR(64),
    reg_date VARCHAR(64),
    id INTEGER PRIMARY KEY
)""") 

db.commit()
logging.debug("[DEBUG] Table 'user' was successfully created")

cur.execute("""CREATE TABLE IF NOT EXISTS article(
    date VARCHAR(64) NULL,
    user_contact VARCHAR(64) NULL,
    user_article INTEGER REFERENCES user(userid) ON UPDATE CASCADE,
    session_time INGEGER,
    id INTEGER PRIMARY KEY
)""") 

db.commit()
logging.debug("[DEBUG] Table 'article' was successfully created")

cur.execute("""CREATE TABLE IF NOT EXISTS question(
    date VARCHAR(64) NULL,
    sender VARCHAR(32),
    sender_chat_id INTEGER NOT NULL,
    content VARCHAR(128),
    id INTEGER PRIMARY KEY
)""")

db.commit() #Apply
logging.debug("[DEBUG] Table 'question' was successfully created")

bot = telebot.TeleBot(bot_info["token"]) #Init bot

@bot.message_handler(content_types=['text','photo'])
def on_text(message):
    if message.text == '/start':
        cur.execute("SELECT chat_id FROM user WHERE chat_id=?",(message.chat.id,)) #Find user in db
        if cur.fetchone() is None:
            cur.execute("INSERT INTO user(chat_id,user_name,first_name,reg_date) VALUES(?,?,?,?)",(
                message.chat.id,
                message.from_user.username,
                message.from_user.first_name,
                str(datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=3),"Europe/Moscow")))
            )) #If user not in db create account 
            db.commit()
            logging.info(f"[INFO] Create new user,chat_id:{message.chat.id}")
            
        msg = """👩‍⚕️Добро пожаловать в бот,психолога Натальи Гринюк.Здесь вы можете *записаться на прием* или *задать вопрос* касающийся психологического здоровья👩‍⚕️"""
        
        if str(message.chat.id) == bot_info["ownerId"]: #If user is owner
            bot.send_photo( #Send welcome message with photo
                message.chat.id,
                open("img/psychologist.jpg","rb"), 
                caption=msg, 
                reply_markup=owner_keyboard(),
                parse_mode="Markdown"
            )
        else:
            bot.send_photo( #Send welcome message with photo
                message.chat.id,
                open("img/psychologist.jpg","rb"),
                caption=msg, 
                reply_markup=main_keyboard(),
                parse_mode="Markdown"
            )
    
    if message.text == "Выгрузить лог📤" and str(message.chat.id) == bot_info["ownerId"]:
        bot.send_message(message.chat.id,"⌛️")
        bot.send_document(message.chat.id,open("log.log","r"),reply_markup=owner_keyboard())
        logging.info("[INFO] Owner successfully got log")
        
    if message.text == "Записи📋" and str(message.chat.id) == bot_info["ownerId"]: #Check all articles,can use only owner
        cur.execute("SELECT * FROM article")
        if cur.fetchone() is not None:
            cur.execute("SELECT * FROM article")
            for article in cur.fetchall():
                session_time = "1:00" if article[4] == 1 else "1:30"
                date = parser.parse(article[0]).strftime(r"%d.%m.%Y") #Article date
                time = parser.parse(article[0]).strftime(r"%H:%M") #Article time
                user = cur.execute("SELECT * FROM user WHERE id=?",(article[2],)).fetchone()
                username = f"@{user[1]}" if user[1] else user[2]
                
                msg = f"🌫Запись №{article[4]}\nДата: *{date}*\nВремя: {time}\nКонтакты: *{article[1]}*\nПользователь: *{username}*\nДлительность сессии: *{session_time}*"
                
                #Delete button for each article
                
                bot.send_message(message.chat.id,msg,parse_mode="Markdown",reply_markup=article_delete_by_owner_keyboard(article[4])) 
            logging.info("[INFO] Owner request all articles")
        else:
            bot.send_message(message.chat.id,"Записей пока что, нет❌",reply_markup=owner_keyboard())
      
    if message.text == "Рассылка📨" and str(message.chat.id) == bot_info["ownerId"]:
        bot.send_message(message.chat.id,"⌛️")
        msg = bot.send_message(message.chat.id,"Введите текст рассылки")
        bot.register_next_step_handler(msg,two_step_newsletter)
            
    if message.text == "Услуги🧑‍⚕️":
        msg = """
            Помогу создать здоровые отношения\n*-С собой*\n*-C партнером*\n*-С деньгами*\n*-С коллегами*\n*-С детьми*\nПрайс-лист:\nСессия *1 час*-4000 руб\nСессия *1.5 часа*-5000 руб"""
        bot.send_message(message.chat.id,"⌛️")
        bot.send_photo(message.chat.id,open("img/psychologist2.jpg","rb"),caption=msg.strip(),parse_mode="Markdown")
        
    if message.text == "Профиль🖥":
        bot.send_message(message.chat.id,"⌛️")
        
        cur.execute("SELECT reg_date FROM user WHERE chat_id=?",(message.chat.id,)) #Get user registration date
        reg_date = parser.parse(cur.fetchone()[0]).strftime(r"%d.%m.%Y") #Parse date from string and format
        
        msg = f"Ваш профиль, {message.from_user.first_name}🖥\nID: *{message.chat.id}*\nДата регистрации: {str(reg_date)}"
        bot.send_message(message.chat.id,msg,parse_mode="Markdown")
    
    if message.text == "Записаться📝":
        bot.send_message(message.chat.id,"⌛️")
        msg = bot.send_message(message.chat.id,"Выберите дату приема",reply_markup=date_choice_keyboard())
        bot.register_next_step_handler(msg,two_step_article)
    
    if message.text == "Задать вопрос❔":
        bot.send_message(message.chat.id,"⌛️")
        msg = bot.send_message(message.chat.id,"Введите вопрос")
        bot.register_next_step_handler(msg,two_step_question_create)
        
    if message.text == "Вопросы❔" and str(message.chat.id) == bot_info["ownerId"]:
        cur.execute("SELECT * FROM question")
        if cur.fetchone() is not None:
            cur.execute("SELECT * FROM question")
            for question in cur.fetchall():
                date = parser.parse(question[0]).strftime(r"%d.%m.%Y %H:%M")
                content = question[3]
                    
                msg = f"*Вопрос №{question[4]}*\nДата создания: {date}\nВопрос: {content}"
                bot.send_message(message.chat.id,msg,parse_mode="Markdown",reply_markup=question_keyboard(question[4]))
        else:
            bot.send_message(message.chat.id,"Вопросов пока что, нет❌",reply_markup=owner_keyboard())

def two_step_newsletter(message):
    cur.execute("SELECT chat_id FROM user")
    for user in cur.fetchall():
        if user[0] != message.chat.id:
            bot.send_message(user[0],message.text,parse_mode="Markdown")
    bot.send_message(message.chat.id,"Рассылка успешно закончилась!",reply_markup=owner_keyboard())
        
    logging.info("[INFO] Owner succesfully create newsletter")
    
def two_step_question_create(message): 
    if len(message.text) >= 10 and len(message.text) <= 128:
        cur.execute("INSERT INTO question(date,sender,sender_chat_id,content) VALUES(?,?,?,?)",(
            str(datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=3),"Europe/Moscow"))),
            message.from_user.username if message.from_user.username is not None else message.from_user.first_name,
            message.chat.id,
            message.text
        )) #If user not in db create account 
        db.commit() #Apply
        
        bot.send_message(message.chat.id,"Вопрос успешно отправлен!",reply_markup=main_keyboard())
        
        logging.info(f"[INFO] User {message.chat.id} successfully created question")
    else:
        bot.send_message(message.chat.id,"Вопрос слишком короткий или длинный!",reply_markup=main_keyboard())
    
def two_step_article(message): 
    """Two step of article create"""
    data = {}
    data["date"] = message.text #Write date from previous step
    if message.text == "Назад◀️":
        bot.send_message(message.chat.id,"Главное меню",reply_markup=main_keyboard())
    else:
        msg = bot.send_message(message.chat.id,"Выберите время приема(МСК)",reply_markup=time_choice_keyboard())
        bot.register_next_step_handler(msg,three_step_article,data=data)
    
def three_step_article(message,data):
    """Three step of article create"""
    data["time"] = message.text #Write time 
    msg = bot.send_message(message.chat.id,"Укажите свои контакты")
    bot.register_next_step_handler(msg,four_step_article,data=data)

def four_step_article(message,data):
    """Four step of article create"""
    data["contact"] = message.text #Write user contact
    msg = bot.send_message(message.chat.id,"Выберите длительность сессии",reply_markup=time_session_keyboard())
    bot.register_next_step_handler(msg,five_step_article,data=data)
    
def five_step_article(message,data):
    """Five step of article create"""
    data["session_time"] = message.text #Write user contact
    
    if data["session_time"] == "1:00":
        data["session_time"] = 1
    elif data["session_time"] == "1:30":
        data["session_time"] = 1.5
    else:
        data["session_time"] = 1
        
    cur.execute("SELECT id FROM user WHERE chat_id=?",(message.chat.id,)) #Get user id from db
    user_id = cur.fetchone()[0]
    
    try:
        date_start = parser.parse(f"{data['date']} {data['time']}") #Time start of session
        end_date = date_start + datetime.timedelta(hours=data["session_time"]) 
        query = """SELECT * FROM article
                WHERE date BETWEEN ? AND ?
        """
        
        cur.execute(query,(date_start,end_date)) #Find article with this date
        if cur.fetchone() is None: #If article with same date not exists
            if len(data["contact"]) >= 8 and len(data["contact"]) < 64:
                cur.execute("INSERT INTO article(date,user_contact,user_article,session_time) VALUES(?,?,?,?)",(
                    str(date_start),
                    data["contact"],
                    user_id,
                    data["session_time"]
                )) #Create article
                db.commit() #Apply
                cur.execute("SELECT id FROM article WHERE date=? AND user_article=?",(str(date_start),user_id))
                
                bot.send_message(message.chat.id,"Ваша заявка успешно создана!\nПсихолог свяжется с вами в назначенную дату и время.",reply_markup=article_cancel_keyboard(cur.fetchone()[0]))
                logging.info(f"[INFO] User {message.chat.id} succesfully created article")
            else:
                bot.send_message(message.chat.id,"Неверно введены данные!",reply_markup=main_keyboard())
        else:
            msg = f"Данное время уже зарезервирванно другим пользователем!"
            bot.send_message(message.chat.id,msg,reply_markup=main_keyboard(),parse_mode="Markdown")
    except ParserError:
        bot.send_message(message.chat.id,"Неверно введены данные!",reply_markup=main_keyboard())
    
def two_step_question_answer(message,data):
    cur.execute("SELECT content,sender_chat_id FROM question WHERE id=?",(data[0])) #Get sender chat id from db
    bot.send_message(cur.fetchone()[1],f"❔Ваш вопрос: {cur.fetchone()[0]}\nОтвет психолога: {message.text}",parse_mode="Markdown") #Send message by chat id e
    bot.send_message(message.chat.id,"Ответ успешно отправлен!")
    
    logging.info(f"[INFO] Owner successfully answer on the question,question_id: {data[0]}")
    
def main_keyboard(): #Main menu keyboard(3 buttons)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=False)
    btn = types.KeyboardButton(text="Записаться📝")
    btn2 = types.KeyboardButton(text="Услуги🧑‍⚕️")
    btn3 = types.KeyboardButton(text="Профиль🖥")
    btn4 = types.KeyboardButton(text="Задать вопрос❔")
    markup.add(btn,btn2,btn3,btn4)
    
    return markup

def owner_keyboard(): #Owner keyboard(3 buttons)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=False)
    btn = types.KeyboardButton(text="Записи📋")
    btn2 = types.KeyboardButton(text="Профиль🖥")
    btn3 = types.KeyboardButton(text="Вопросы❔")
    btn4 = types.KeyboardButton(text="Выгрузить лог📤")
    btn5 = types.KeyboardButton(text="Рассылка📨")
    markup.add(btn,btn2,btn3,btn4,btn5)
    
    return markup

def date_choice_keyboard(): #Date choice keyboard(14 buttons)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=True,row_width=3)

    row = []
    date = datetime.datetime.now() #Get current date
    for i in range(1,14): #Create button for choice date
        date = (date + datetime.timedelta(days=1))
        btn = types.KeyboardButton(text=str(date.strftime(r"%d.%m")))
        row.append(btn)
        if len(row) == 3:
            markup.row(*row)
            row = []
            
    go_back_btn = types.KeyboardButton(text="Назад◀️")
    markup.add(go_back_btn)
    
    return markup

def time_choice_keyboard(): #Time choice keyboard(8 buttons)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=True)
    time_intervals = ['13:00', '13:30', '14:00', '14:30',
                      '15:00', '15:30', '16:00', '16:30',
                      '17:00', '17:30', '18:00', '18:30',
                      '19:00', '19:30', '20:00'
    ]
    buttons = [types.KeyboardButton(interval) for interval in time_intervals]
    row = []    
        
    for btn in buttons: #Create 12 buttons with time 13-20
        row.append(btn)
    
        if len(row) == 3:
            markup.row(*row)
            row = []
            
    return markup

def article_cancel_keyboard(id): #When user want delete article
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton(text="Отменить❌",callback_data=f"deleteByUser_{id}")
    btn2 = types.InlineKeyboardButton(text="Главное меню🎛",callback_data="backToMainMenu")
    markup.add(btn,btn2)
    
    return markup

def article_delete_by_owner_keyboard(id):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton(text="Удалить❌", callback_data=f"deleteByOwner_{id}")
    markup.add(btn)
    
    return markup

def question_keyboard(id):
    markup = types.InlineKeyboardMarkup() 
    btn = types.InlineKeyboardButton(text="Ответить✉️",callback_data=f"reply_{id}")
    btn2 = types.InlineKeyboardButton(text="Удалить❌",callback_data=f"deleteQuestion_{id}")
    markup.add(btn,btn2)
    
    return markup

@bot.callback_query_handler(func = lambda call: True)
def answer(call):
    if call.data == "backToMainMenu":
        bot.edit_message_reply_markup(call.message.chat.id,call.message.id)
        bot.send_message(call.message.chat.id,"⌛️",reply_markup=main_keyboard())

    if call.data.startswith("deleteByOwner_"):  
        article_id = call.data.split('_')[1]
        cur.execute("DELETE FROM article WHERE id=?", (article_id,)) #Delete article
        db.commit() #Apply
        
        bot.answer_callback_query(call.id, "Запись удалена❌") #Notiflication about delete message
        bot.delete_message(call.message.chat.id,call.message.message_id)

        logging.info(f"[INFO] Owner successfully delete article,article_id: {article_id}")

    if call.data.startswith("deleteByUser_"):  
        article_id = call.data.split('_')[1]
        cur.execute("DELETE FROM article WHERE id=?", (article_id,)) #Delete article
        db.commit() #Apply
        
        bot.answer_callback_query(call.id, "Запись удалена❌") #Notiflication about delete message
        bot.delete_message(call.message.chat.id,call.message.message_id)
        bot.send_message(call.message.chat.id,"⌛️",reply_markup=main_keyboard())
        logging.info(f"[INFO] User {call.message.chat.id} successfully delete article,article_id:{article_id}")
    
    if call.data.startswith("deleteQuestion_"):
        question_id = call.data.split('_')[1]

        cur.execute("DELETE FROM question WHERE id=?", (question_id,)) #Delete article
        db.commit() #Apply
        
        bot.answer_callback_query(call.id, "Вопрос удален❌") #Notiflication about delete message
        bot.delete_message(call.message.chat.id,call.message.message_id)

        logging.info(f"[INFO] Owner successfully delete question,question_id: {question_id}")
    
    if call.data.startswith("reply_"):
        question_id = call.data.split('_')[1]            
        msg = bot.send_message(call.message.chat.id,"Введите ответ для пользователя!")
        
        bot.register_next_step_handler(msg,two_step_question_answer,data=(question_id))
    
def time_session_keyboard():    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    btn = types.KeyboardButton(text="1:00")    
    btn2 = types.KeyboardButton(text="1:30") 
    markup.add(btn,btn2)
    
    return markup
    
bot.infinity_polling()