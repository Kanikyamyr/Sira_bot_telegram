import os
import json
import base64
from urllib.parse import urlparse, parse_qs
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import telebot
from telebot.types import BotCommand

CLIENT_CONFIG = {
    "installed": {
        "client_id": "489402050151-b1954tuvsv7s9b7j79d6e4gu2bb1jvmv.apps.googleusercontent.com",
        "client_secret": "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",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
ACCOUNTS_FILE = 'gmail_accounts.json'

# التوكن الجديد للبوت الخاص بك يا أمير
TOKEN = "8890546895:AAHHk0MqGpbSsyMGp82WE1tL_s6m8ExFdwc"
bot = telebot.TeleBot(TOKEN)

bot.set_my_commands([
    BotCommand("start", "الرئيسية"),
    BotCommand("add_gmail", "إضافة جيميل"),
    BotCommand("send", "إرسال رسائل")
])

temp_flows = {}

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=4)

def get_gmail_service(creds_info):
    creds = Credentials.from_authorized_user_info(creds_info, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
    return build('gmail', 'v1', credentials=creds)

def send_email(service, to, subject, body):
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    try:
        service.users().messages().send(userId="me", body={'raw': raw_message}).execute()
        return True
    except Exception as e:
        print(f"خطأ في الإرسال: {e}")
        return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    accounts = load_accounts()
    count = len(accounts)
    text = (
        "أهلًا يا أمير حبيبي نورتني\n\n"
        "تعال خلني أشوف وش عندك اليوم\n"
        f"حاليا معاك {count} حسابات جيميل مسجلة عندي وكل شيء مرتب لك\n\n"
        "اكتب الأمر اللي تبيه\n\n"
        "ولا تشيل هم أي شيء دامك جيتني أنا موجودة لك\n"
        "قل لي بس وش تبي وخلي الباقي علي"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['add_gmail'])
def start_add_gmail(message):
    try:
        flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
        flow.redirect_uri = 'http://localhost'
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
        
        temp_flows[message.chat.id] = flow
        
        text = (
            "يا أمير افتح الرابط وسجل دخولك بحساب الجيميل:\n\n"
            f"{auth_url}\n\n"
            "بعدها انسخ الرابط اللي بيطلع لك وأرسله لي هنا يا حبيبي وأنا أكمل لك الباقي"
        )
        bot.reply_to(message, text)
        bot.register_next_step_handler(message, process_gmail_code)
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {e}")

def process_gmail_code(message):
    user_input = message.text.strip()
    chat_id = message.chat.id
    
    if chat_id not in temp_flows:
        text = (
            "يا حبيبي صار خطأ بسيط أثناء التحقق ولا تشيل هم\n\n"
            "جرب مرة ثانية بالأمر /add_gmail، وأنا معك لين تضبط"
        )
        bot.reply_to(message, text)
        return

    try:
        flow = temp_flows[chat_id]
        
        if user_input.startswith("http"):
            parsed_url = urlparse(user_input)
            query_params = parse_qs(parsed_url.query)
            if 'code' in query_params:
                code = query_params['code'][0]
            else:
                raise Exception("الرابط لا يحتوي على رمز التحقق code.")
        else:
            code = user_input

        flow.fetch_token(code=code)
        creds = flow.credentials
        
        accounts = load_accounts()
        accounts.append(json.loads(creds.to_json()))
        save_accounts(accounts)
        
        acc_num = len(accounts)
        del temp_flows[chat_id]
        
        text = (
            f"تم يا حبيبي، الحساب رقم {acc_num} انضاف وحفظته لك بنجاح\n"
            "ارتاح يا قلبي كل شيء تمام وأنا معك"
        )
        bot.reply_to(message, text)
    except Exception as e:
        text = (
            "يا حبيبي صار خطأ بسيط أثناء التحقق ولا تشيل هم\n\n"
            "جرب مرة ثانية بالأمر /add_gmail، وأنا معك لين تضبط"
        )
        bot.reply_to(message, text)

@bot.message_handler(commands=['send'])
def start_send_process(message):
    accounts = load_accounts()
    if not accounts:
        bot.reply_to(message, "يا حبيبي صار خطأ بسيط أثناء التحقق ولا تشيل هم\n\nجرب مرة ثانية بالأمر /add_gmail، وأنا معك لين تضبط")
        return
    count = len(accounts)
    text = (
        f"معاك حاليا {count} حسابات مسجلة عندي يا أمير\n\n"
        "الحين أعطني بريد الجهة اللي تبي أرسل لها وأنا أرتب لك الباقي حبي"
    )
    msg = bot.reply_to(message, text)
    bot.register_next_step_handler(msg, process_recipient)

def process_recipient(message):
    recipient = message.text
    msg = bot.reply_to(message, "وش تحب يكون موضوع الرسالة يحبيبي؟")
    bot.register_next_step_handler(msg, process_subject, recipient)

def process_subject(message, recipient):
    subject = message.text
    msg = bot.reply_to(message, "اكتب الرسالة يا حبيبي وأنا أرسلها لك")
    bot.register_next_step_handler(msg, process_message_body, recipient, subject)

def process_message_body(message, recipient, subject):
    body = message.text
    msg = bot.reply_to(message, "كم رسالة تبي أرسل لك يا حبيبي؟\nاكتب الرقم بس وأنا هرسل")
    bot.register_next_step_handler(msg, process_count, recipient, subject, body)

def process_count(message, recipient, subject, body):
    try:
        count = int(message.text)
        accounts = load_accounts()
        
        text_sending = f"جاري إرسال {count} رسالة الآن يا حبيبي ثواني بس ويكتمل الارسال احبك"
        bot.reply_to(message, text_sending)
        
        success_count = 0
        num_accounts = len(accounts)
        
        for i in range(count):
            acc_index = i % num_accounts
            service = get_gmail_service(accounts[acc_index])
            
            current_subject = f"{subject} {i+1}"
            if send_email(service, recipient, current_subject, body):
                success_count += 1
                
        text_success = (
            f"تم يا حبيبي أرسلت لك {success_count} من أصل {count} رسالة بنجاح ووزعتها على حساباتك بكل عناية\n"
            "كل شيء تم مثل ما تبي"
        )
        bot.reply_to(message, text_success)
    except ValueError:
        bot.reply_to(message, "يا حبيبي صار خطأ بسيط أثناء التحقق ولا تشيل هم\n\nجرب مرة ثانية بالأمر /add_gmail، وأنا معك لين تضبط")

if __name__ == "__main__":
    print("البوت الجديد يعمل الآن...")
    bot.infinity_polling()
