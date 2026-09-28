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
from telebot.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton


# =========================================================
# Google OAuth
# =========================================================

CLIENT_CONFIG = {
    "installed": {
        "client_id": "P489402050151-pveriror0urrulgs1tplj5gfgptoldg5.apps.googleusercontent.com",
        "client_secret": "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",
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

TOKEN = "8859368953:AAENxBV3_gwVikQFxp_wTwQg8qtn8liTNvA"

bot = telebot.TeleBot(TOKEN)


# =========================================================
# صاحب البوت فقط
# =========================================================

AUTHORIZED_USER_ID = 6806665096


@bot.message_handler(
    func=lambda message: message.from_user.id != AUTHORIZED_USER_ID
)
def block_unauthorized_users(message):

    bot.reply_to(
        message,
        "آسفة حبيبي، هذا البوت لأمير فقط 🤍"
    )


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

            with open(
                ACCOUNTS_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except Exception:

            return []

    return []


def save_accounts(accounts):

    with open(
        ACCOUNTS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            accounts,
            f,
            indent=4,
            ensure_ascii=False
        )


# =========================================================
# Gmail Profile
# =========================================================

def get_gmail_email(creds):

    service = build(
        "gmail",
        "v1",
        credentials=creds
    )

    profile = service.users().getProfile(
        userId="me"
    ).execute()

    return profile.get(
        "emailAddress",
        ""
    )


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

        creds.refresh(
            Request()
        )

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

            message.attach(
                image
            )

        message["to"] = to

        # العنوان اختياري
        if subject:
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

        print(
            f"خطأ في الإرسال: {e}"
        )

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

        # معرفة البريد الحقيقي للحساب
        email = get_gmail_email(
            creds
        )

        accounts = load_accounts()

        account_data = json.loads(
            creds.to_json()
        )

        # حفظ البريد مع بيانات الحساب
        account_data["email"] = email

        # اسم الحساب الافتراضي
        account_data["name"] = email

        accounts.append(
            account_data
        )

        save_accounts(
            accounts
        )

        acc_num = len(accounts)

        del temp_flows[chat_id]

        text = (
            f"تم يا حبيبي، الحساب رقم {acc_num} انضاف وحفظته لك بنجاح\n\n"
            f"📧 الحساب: {email}"
        )

        bot.reply_to(
            message,
            text
        )

    except Exception as e:

        print(
            f"OAuth ERROR: {repr(e)}"
        )

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
    failed_count = 0

    changed = False

    keyboard = InlineKeyboardMarkup()

    for index, acc in enumerate(accounts, 1):

        email = acc.get(
            "email",
            ""
        )

        name = acc.get(
            "name",
            ""
        )

        try:

            creds = Credentials.from_authorized_user_info(
                acc,
                SCOPES
            )

            if not creds:

                raise Exception(
                    "بيانات التوثيق غير موجودة"
                )

            if creds.expired:

                if creds.refresh_token:

                    from google.auth.transport.requests import Request

                    creds.refresh(
                        Request()
                    )

                else:

                    raise Exception(
                        "يحتاج إعادة تسجيل الدخول"
                    )

            if not creds.valid:

                raise Exception(
                    "التوثيق غير صالح"
                )

            # إذا الحساب قديم وما عنده إيميل
            if not email:

                try:

                    email = get_gmail_email(
                        creds
                    )

                    acc["email"] = email
                    changed = True

                except Exception:

                    email = "البريد غير معروف"

            if not name:

                name = email
                acc["name"] = name
                changed = True

            working_count += 1

            report.append(
                f"🟢 الحساب {index}\n"
                f"👤 الاسم: {name}\n"
                f"📧 Gmail: {email}\n"
                f"✅ الحالة: فعال\n"
            )

        except Exception as e:

            failed_count += 1

            error = str(e).lower()

            if "invalid_grant" in error:

                status = "يحتاج إعادة تسجيل الدخول"

            elif "refresh" in error:

                status = "مشكلة في تحديث التوثيق"

            else:

                status = "التوثيق غير صالح"

            if not email:
                email = "البريد غير معروف"

            if not name:
                name = email

            report.append(
                f"🔴 الحساب {index}\n"
                f"👤 الاسم: {name}\n"
                f"📧 Gmail: {email}\n"
                f"❌ الحالة: {status}\n"
            )

        # زر حذف الحساب
        keyboard.add(
            InlineKeyboardButton(
                f"🗑 حذف الحساب {index}",
                callback_data=f"delete_account:{index - 1}"
            )
        )

    if changed:

        save_accounts(
            accounts
        )

    result_text = (
        f"تقرير فحص الحسابات "
        f"({working_count}/{len(accounts)} شغالة):\n\n"
        + "\n".join(report)
        + "\n"
        + "يا أمير إذا لقيت حساب فيه مشكلة وتبي تشيله، "
        "اضغط زر الحذف الخاص فيه تحت 🤍\n\n"
        "وبعدها تقدر تضيفه من جديد بالأمر /add_gmail."
    )

    bot.send_message(
        message.chat.id,
        result_text,
        reply_markup=keyboard
    )


# =========================================================
# حذف الحساب
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("delete_account:")
)
def delete_account_callback(call):

    if call.from_user.id != AUTHORIZED_USER_ID:

        bot.answer_callback_query(
            call.id,
            "هذا البوت لأمير فقط 🤍",
            show_alert=True
        )

        return

    try:

        index = int(
            call.data.split(":")[1]
        )

        accounts = load_accounts()

        if index < 0 or index >= len(accounts):

            bot.answer_callback_query(
                call.id,
                "الحساب غير موجود.",
                show_alert=True
            )

            return

        account = accounts[index]

        email = account.get(
            "email",
            "البريد غير معروف"
        )

        name = account.get(
            "name",
            email
        )

        accounts.pop(
            index
        )

        save_accounts(
            accounts
        )

        bot.answer_callback_query(
            call.id,
            "تم حذف الحساب 🤍"
        )

        bot.send_message(
            call.message.chat.id,
            "تم يا أمير حبيبي، حذفت لك الحساب 🤍\n\n"
            f"👤 الاسم: {name}\n"
            f"📧 Gmail: {email}\n\n"
            "وإذا تبيه من جديد، أضفه بالأمر /add_gmail."
        )

    except Exception as e:

        print(
            f"Delete ERROR: {repr(e)}"
        )

        bot.answer_callback_query(
            call.id,
            "صار خطأ أثناء حذف الحساب.",
            show_alert=True
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
        "وش تحب يكون موضوع الرسالة يحبيبي؟\n\n"
        "إذا ما تبي عنوان، ارسل لي «لا» أو «ما أبي عنوان» "
        "وأخليها بدون عنوان."
    )

    bot.register_next_step_handler(
        msg,
        process_subject,
        recipient
    )


# =========================================================
# Subject
# =========================================================

def process_subject(
    message,
    recipient
):

    subject = message.text.strip()

    no_subject_words = [
        "لا",
        "ل",
        "no",
        "n",
        "بدون عنوان",
        "ما أبي عنوان",
        "ما ابي عنوان",
        "لا أبي عنوان",
        "لا ابي عنوان",
        "بدون",
        "فارغ",
        "فاضي"
    ]

    if subject.lower() in no_subject_words:

        subject = ""

    msg = bot.reply_to(
        message,
        "اكتب الرسالة يا حبيبي وأنا أرسلها لك\n\n"
        "وإذا ما تبي رسالة، ارسل لي «لا» أو «ما أبي رسالة» "
        "وأخلي الإيميل بدون رسالة."
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

    no_message_words = [
        "لا",
        "ل",
        "no",
        "n",
        "بدون رسالة",
        "ما أبي رسالة",
        "ما ابي رسالة",
        "لا أبي رسالة",
        "لا ابي رسالة",
        "بدون",
        "فارغ",
        "فاضي"
    ]

    if body.strip().lower() in no_message_words:

        body = ""

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
        "يغبي اكتب فقط: نعم أو لا"
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
                "أرسل صورة يا حبيبي، وليس نصاً."
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
                "\n\nاحبك"
            )

        else:

            text_sending += (
                "\n\n"
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

                # العنوان يبقى كما أدخله أمير
                # وإذا اختار بدون عنوان سيكون فارغاً
                current_subject = subject

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
