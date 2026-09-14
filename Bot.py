import os
import json
import base64
import time
from urllib.parse import urlparse, parse_qs
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import telebot
from telebot.types import BotCommand


# =========================================================
# Google OAuth
# =========================================================

CLIENT_CONFIG = {
    "installed": {
        "client_id": "PUT_YOUR_NEW_CLIENT_ID_HERE",
        "client_secret": "PUT_YOUR_NEW_CLIENT_SECRET_HERE",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]

ACCOUNTS_FILE = "gmail_accounts.json"


# =========================================================
# Telegram Bot
# =========================================================

TOKEN = "8890546895:AAHHk0MqGpbSsyMGp82WE1tL_s6m8ExFdwc"

bot = telebot.TeleBot(TOKEN)


bot.set_my_commands([
    BotCommand("start", "الرئيسية"),
    BotCommand("add_gmail", "إضافة جيميل"),
    BotCommand("check_accounts", "فحص الحسابات"),
    BotCommand("send", "إرسال رسائل")
])


# =========================================================
# Temporary OAuth flows
# =========================================================

temp_flows = {}


# =========================================================
# Gmail Accounts
# =========================================================

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []

    return []


def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=4)


# =========================================================
# Gmail Service
# =========================================================

def get_gmail_service(creds_info):
    creds = Credentials.from_authorized_user_info(
        creds_info,
        SCOPES
    )

    if creds and creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())

    return build(
        "gmail",
        "v1",
        credentials=creds
    )


# =========================================================
# Send Email
# =========================================================

def send_email(
    service,
    to,
    subject,
    body,
    image_bytes=None,
    image_filename="image.jpg"
):
    try:

        # بدون صورة
        if image_bytes is None:

            message = MIMEText(
                body,
                "plain",
                "utf-8"
            )

        # مع صورة
        else:

            message = MIMEMultipart()

            message.attach(
                MIMEText(
                    body,
                    "plain",
                    "utf-8"
                )
            )

            image = MIMEImage(
                image_bytes,
                _subtype="jpeg"
            )

            image.add_header(
                "Content-Disposition",
                "attachment",
                filename=image_filename
            )

            message.attach(image)

        message["to"] = to
        message["subject"] = subject

        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        service.users().messages().send(
            userId="me",
            body={
                "raw": raw_message
            }
        ).execute()

        return True

    except Exception as e:

        print(f"خطأ في الإرسال: {e}")

        return False


# =========================================================
# /start
# =========================================================

@bot.message_handler(commands=["start"])
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

    bot.reply_to(
        message,
        text
    )


# =========================================================
# /add_gmail
# =========================================================

@bot.message_handler(commands=["add_gmail"])
def start_add_gmail(message):

    try:

        flow = InstalledAppFlow.from_client_config(
            CLIENT_CONFIG,
            SCOPES
        )

        flow.redirect_uri = "http://localhost"

        auth_url, _ = flow.authorization_url(
            prompt="consent",
            access_type="offline",
            include_granted_scopes="true"
        )

        temp_flows[message.chat.id] = flow

        text = (
            "يا أمير افتح الرابط وسجل دخولك بحساب الجيميل:\n\n"
            f"{auth_url}\n\n"
            "بعدها انسخ الرابط اللي بيطلع لك وأرسله لي هنا يا حبيبي وأنا أكمل لك الباقي"
        )

        bot.reply_to(
            message,
            text
        )

        bot.register_next_step_handler(
            message,
            process_gmail_code
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"حدث خطأ: {e}"
        )


def process_gmail_code(message):

    user_input = message.text.strip()
    chat_id = message.chat.id

    if chat_id not in temp_flows:

        text = (
            "يا حبيبي صار خطأ بسيط أثناء التحقق ولا تشيل هم\n\n"
            "جرب مرة ثانية بالأمر /add_gmail، وأنا معك لين تضبط"
        )

        bot.reply_to(
            message,
            text
        )

        return

    try:

        flow = temp_flows[chat_id]

        if user_input.startswith("http"):

            parsed_url = urlparse(
                user_input
            )

            query_params = parse_qs(
                parsed_url.query
            )

            if "code" in query_params:

                code = query_params["code"][0]

            else:

                raise Exception(
                    "الرابط لا يحتوي على رمز التحقق code."
                )

        else:

            code = user_input

        flow.fetch_token(
            code=code
        )

        creds = flow.credentials

        accounts = load_accounts()

        accounts.append(
            json.loads(
                creds.to_json()
            )
        )

        save_accounts(
            accounts
        )

        acc_num = len(accounts)

        del temp_flows[chat_id]

        text = (
            f"تم يا حبيبي، الحساب رقم {acc_num} انضاف وحفظته لك بنجاح\n"
            "ارتاح يا قلبي كل شيء تمام وأنا معك"
        )

        bot.reply_to(
            message,
            text
        )

    except Exception:

        text = (
            "يا حبيبي صار خطأ بسيط أثناء التحقق ولا تشيل هم\n\n"
            "جرب مرة ثانية بالأمر /add_gmail، وأنا معك لين تضبط"
        )

        bot.reply_to(
            message,
            text
        )


# =========================================================
# /check_accounts
# =========================================================

@bot.message_handler(commands=["check_accounts"])
def check_accounts_command(message):

    accounts = load_accounts()

    if not accounts:

        bot.reply_to(
            message,
            "يا أمير ما فيه أي حسابات مسجلة عندي حالياً. أضف حسابات بالأمر /add_gmail"
        )

        return

    bot.reply_to(
        message,
        f"جاري فحص {len(accounts)} حسابات مسجلة يا أمير، ثواني بس..."
    )

    report = []
    working_count = 0

    for index, acc in enumerate(accounts, 1):

        try:

            creds = Credentials.from_authorized_user_info(
                acc,
                SCOPES
            )

            if not creds:

                report.append(
                    f"❌ الحساب {index}: بيانات التوثيق غير موجودة"
                )

                continue

            if creds.expired:

                if creds.refresh_token:

                    from google.auth.transport.requests import Request

                    creds.refresh(
                        Request()
                    )

                else:

                    report.append(
                        f"❌ الحساب {index}: يحتاج إعادة تسجيل الدخول"
                    )

                    continue

            if creds.valid:

                working_count += 1

                report.append(
                    f"✅ الحساب {index}: التوثيق شغال"
                )

            else:

                report.append(
                    f"❌ الحساب {index}: التوثيق غير صالح"
                )

        except Exception as e:

            error = str(e).lower()

            if "invalid_grant" in error:

                report.append(
                    f"❌ الحساب {index}: يحتاج إعادة تسجيل الدخول"
                )

            elif "refresh" in error:

                report.append(
                    f"❌ الحساب {index}: مشكلة في تحديث التوثيق"
                )

            else:

                report.append(
                    f"❌ الحساب {index}: مشكلة في التوثيق"
                )

    result_text = (
        f"تقرير فحص الحسابات "
        f"({working_count}/{len(accounts)} شغالة):\n\n"
        + "\n".join(report)
    )

    bot.reply_to(
        message,
        result_text
    )


# =========================================================
# /send
# =========================================================

@bot.message_handler(commands=["send"])
def start_send_process(message):

    accounts = load_accounts()

    if not accounts:

        bot.reply_to(
            message,
            "يا حبيبي ما عندك أي حسابات جيميل مسجلة حالياً.\n\n"
            "أضف حساب بالأمر /add_gmail"
        )

        return

    count = len(accounts)

    text = (
        f"معاك حاليا {count} حسابات مسجلة عندي يا أمير\n\n"
        "الحين أعطني بريد الجهة اللي تبي أرسل لها وأنا أرتب لك الباقي حبي"
    )

    msg = bot.reply_to(
        message,
        text
    )

    bot.register_next_step_handler(
        msg,
        process_recipient
    )


# =========================================================
# Recipient
# =========================================================

def process_recipient(message):

    recipient = message.text.strip()

    msg = bot.reply_to(
        message,
        "وش تحب يكون موضوع الرسالة يحبيبي؟"
    )

    bot.register_next_step_handler(
        msg,
        process_subject,
        recipient
    )


# =========================================================
# Subject
# =========================================================

def process_subject(message, recipient):

    subject = message.text.strip()

    msg = bot.reply_to(
        message,
        "اكتب الرسالة يا حبيبي وأنا أرسلها لك"
    )

    bot.register_next_step_handler(
        msg,
        process_message_body,
        recipient,
        subject
    )


# =========================================================
# Message Body
# =========================================================

def process_message_body(
    message,
    recipient,
    subject
):

    body = message.text

    msg = bot.reply_to(
        message,
        "هل تريد إرفاق صورة مع الإيميل؟\n\n"
        "اكتب: نعم أو لا"
    )

    bot.register_next_step_handler(
        msg,
        process_attachment_choice,
        recipient,
        subject,
        body
    )


# =========================================================
# Attachment Choice
# =========================================================

def process_attachment_choice(
    message,
    recipient,
    subject,
    body
):

    choice = message.text.strip().lower()

    yes_words = [
        "نعم",
        "ن",
        "yes",
        "y"
    ]

    no_words = [
        "لا",
        "ل",
        "no",
        "n"
    ]

    if choice in yes_words:

        msg = bot.reply_to(
            message,
            "تمام يا حبيبي، أرسل الصورة الآن"
        )

        bot.register_next_step_handler(
            msg,
            process_attachment_photo,
            recipient,
            subject,
            body
        )

        return

    if choice in no_words:

        ask_for_count(
            message,
            recipient,
            subject,
            body,
            None,
            None
        )

        return

    msg = bot.reply_to(
        message,
        "اكتب فقط: نعم أو لا"
    )

    bot.register_next_step_handler(
        msg,
        process_attachment_choice,
        recipient,
        subject,
        body
    )


# =========================================================
# Receive Photo
# =========================================================

def process_attachment_photo(
    message,
    recipient,
    subject,
    body
):

    try:

        if not message.photo:

            msg = bot.reply_to(
                message,
                "أرسل صورة يا حبيبي، وليس نصاً.\n\n"
                "أرسل الصورة الآن"
            )

            bot.register_next_step_handler(
                msg,
                process_attachment_photo,
                recipient,
                subject,
                body
            )

            return

        # أكبر نسخة من الصورة
        photo = message.photo[-1]

        file_info = bot.get_file(
            photo.file_id
        )

        image_bytes = bot.download_file(
            file_info.file_path
        )

        image_filename = os.path.basename(
            file_info.file_path
        )

        ask_for_count(
            message,
            recipient,
            subject,
            body,
            image_bytes,
            image_filename
        )

    except Exception as e:

        bot.reply_to(
            message,
            "صار خطأ أثناء تحميل الصورة.\n"
            "جرب الأمر /send مرة ثانية."
        )

        print(
            f"خطأ تحميل الصورة: {e}"
        )


# =========================================================
# Ask Number Of Messages
# =========================================================

def ask_for_count(
    message,
    recipient,
    subject,
    body,
    image_bytes,
    image_filename
):

    msg = bot.reply_to(
        message,
        "كم رسالة تبي أرسل لك يا حبيبي؟\n"
        "اكتب الرقم بس وأنا هرسل"
    )

    bot.register_next_step_handler(
        msg,
        process_count,
        recipient,
        subject,
        body,
        image_bytes,
        image_filename
    )


# =========================================================
# Process Count + Send
# =========================================================

def process_count(
    message,
    recipient,
    subject,
    body,
    image_bytes=None,
    image_filename=None
):

    try:

        count = int(
            message.text.strip()
        )

        if count <= 0:

            bot.reply_to(
                message,
                "اكتب رقم أكبر من صفر يا حبيبي"
            )

            return

        accounts = load_accounts()

        if not accounts:

            bot.reply_to(
                message,
                "ما فيه حسابات جيميل مسجلة حالياً."
            )

            return

        text_sending = (
            f"جاري إرسال {count} رسالة الآن يا حبيبي، "
            "ثواني بس ويكتمل الإرسال"
        )

        if image_bytes is not None:

            text_sending += (
                "\n\nتبي ارسلك صوره مع الرساله؟"
            )

        else:

            text_sending += (
                "\n\nاو بدون صور ي امير؟"
            )

        bot.reply_to(
            message,
            text_sending
        )

        success_count = 0

        num_accounts = len(accounts)

        for i in range(count):

            acc_index = i % num_accounts

            try:

                service = get_gmail_service(
                    accounts[acc_index]
                )

                current_subject = (
                    f"{subject} {i + 1}"
                )

                if send_email(
                    service,
                    recipient,
                    current_subject,
                    body,
                    image_bytes,
                    image_filename
                ):

                    success_count += 1

            except Exception as e:

                print(
                    f"خطأ في الحساب {acc_index + 1}: {e}"
                )

            # مهلة بين الرسائل
            time.sleep(2)

        text_success = (
            f"تم يا حبيبي، أرسلت لك "
            f"{success_count} من أصل {count} رسالة بنجاح\n"
        )

        if image_bytes is not None:

            text_success += (
                "والصورة كانت مرفقة مع الرسائل حبي"
            )

        else:

            text_success += (
                "والإرسال كان بدون صورة حبي"
            )

        bot.reply_to(
            message,
            text_success
        )

    except ValueError:

        bot.reply_to(
            message,
            "يا حبيبي اكتب رقم صحيح فقط، مثل:\n"
            "5"
        )

    except Exception as e:

        print(
            f"خطأ في عملية الإرسال: {e}"
        )

        bot.reply_to(
            message,
            "صار خطأ أثناء عملية الإرسال.\n"
            "راجع سجل البوت وجرب مرة ثانية."
        )


# =========================================================
# Run Bot
# =========================================================

if __name__ == "__main__":

    print(
        "البوت الجديد يعمل الآن..."
    )

    bot.infinity_polling()
