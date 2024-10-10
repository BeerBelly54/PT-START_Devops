import logging
import re
import os
import paramiko
import asyncio
import subprocess

from dotenv import load_dotenv
from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes, CallbackQueryHandler
from subprocess import run

import asyncpg

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('TOKEN')
RM_HOST = os.getenv('RM_HOST')
RM_PORT = int(os.getenv('RM_PORT'))
RM_USER = os.getenv('RM_USER')
RM_PASSWORD = os.getenv('RM_PASSWORD')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_DATABASE = os.getenv('DB_DATABASE')
# Настройка логгирования
logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


# Функция команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f'Привет {user.full_name}!')
    await update.message.reply_text(f'Напиши /help для получения списка команд!')

# Функция команды /help
async def helpCommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        "/start - Запустить бота",
        "/find_emails - Найти email-адреса в тексте",
        "/find_phone_number - Найти номера телефонов в тексте",
        "/verify_password - Проверить пароль на сложность",

        "\nКоманды для мониторинга Linux системы: \n",
        "/get_release - Вывести версию системы",
        "/get_uname - Вывести информацию об архитектуре процессора, имени хоста системы и версии ядра",
        "/get_uptime - Вывести время работы системы",
        "/get_df - Вывести информацию о состоянии файловой системы",
        "/get_free - Вывести свободное место на диске",
        "/get_mpstat - Вывести информацию о производительности системы",
        "/get_w - Вывести информацию о работающих в системе пользователях",
        "/get_auths - Вывести список 10 последних входов в систему",
        "/get_critical - Вывести последние 5 критических событий",
        "/get_ps - Вывести список запущенных процессов",
        "/get_ss - Вывести список используемых портов",
        "/get_apt_list - Вывести список установленных пакетов",
        "/get_services - Вывести список запущенных сервисов",
        "/get_repl_logs - Вывести логи репликации с Master сервера",
        "/get_emails - Вывести список email-адресов из базы данных",
        "/get_phone_numbers - Вывести список номеров телефонов из базы данных", 
    ]
    help_text = "Доступные команды:\n\n" + "\n".join(commands)
    await update.message.reply_text(help_text)

# Функция обработки неизвестных команд
async def unknownCommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неправильная команда. Используйте /help для вывода списка доступных команд.")

# Функция команды echo
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Операция отменена.')
    return ConversationHandler.END

# Функция команды /find_email
async def find_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Пожалуйста, отправьте текст для поиска email-адресов.')
    return 'EMAIL'

# Функция команды /find_phone_number
async def find_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Пожалуйста, отправьте текст для поиска номеров телефонов.')
    return 'PHONE'

# Функция обработки email-адресов
async def extract_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if emails:
        context.user_data['emails'] = emails
        await update.message.reply_text(f'Найденные email-адреса: {", ".join(emails)}\nХотите записать их в базу данных? (да/нет)')
        return 'CONFIRM_EMAIL'
    else:
        await update.message.reply_text('Email-адреса не найдены.')
    return ConversationHandler.END

# Функция обработки номеров телефонов
async def extract_phone_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    phone_numbers = re.findall(r'(?:\+7|8)[-\s]?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}', text)
    if phone_numbers:
        context.user_data['phone_numbers'] = phone_numbers
        await update.message.reply_text(f'Найденные номера телефонов: {", ".join(phone_numbers)}\nХотите записать их в базу данных? (да/нет)')
        return 'CONFIRM_PHONE'
    else:
        await update.message.reply_text('Номера телефонов не найдены.')
    return ConversationHandler.END

# Функция подтверждения записи email-адресов в базу данных
async def confirm_save_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = update.message.text.lower()
    if response == 'да':
        emails = context.user_data.get('emails', [])
        command = f"INSERT INTO emails (email) VALUES {', '.join([f'({email!r})' for email in emails])} RETURNING id"
        result = await asyncpg_connection(command)
        if result:
            await update.message.reply_text('Email-адреса успешно записаны в базу данных.')
        else:
            await update.message.reply_text('Произошла ошибка при записи в базу данных.')
    else:
        await update.message.reply_text('Запись в базу данных отменена.')
    return ConversationHandler.END

# Функция подтверждения записи номеров телефонов в базу данных
async def confirm_save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = update.message.text.lower()
    if response == 'да':
        phone_numbers = context.user_data.get('phone_numbers', [])
        command = f"INSERT INTO numbers (phone_number) VALUES {', '.join([f'({phone_number})' for phone_number in phone_numbers])} RETURNING id"
        result = await asyncpg_connection(command)
        if result:
            await update.message.reply_text('Номера телефонов успешно записаны в базу данных.')
        else:
            await update.message.reply_text('Произошла ошибка при записи в базу данных.')
    else:
        await update.message.reply_text('Запись в базу данных отменена.')
    return ConversationHandler.END

# Функция команды /verify_password
async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Пожалуйста, отправьте пароль для проверки.')
    return 'PASSWORD'
    
# Функция проверки сложности пароля
async def is_strong_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()])[A-Za-z\d!@#$%^&*()]{8,}$'
    
    if re.match(pattern, password):
        await update.message.reply_text('Пароль сложный')
    else:
        await update.message.reply_text('Пароль простой')
    return ConversationHandler.END

# Функция выполнения команды на удаленном сервере по SSH
async def ssh_command(command):
    """Выполнение команды на удаленном сервере через SSH"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
    stdin, stdout, stderr = client.exec_command(command)
    result = stdout.read().decode('utf-8')
    client.close()
    return result

# Функции команд для вывода информации на удаленном сервере

# Функция вывода информации о релизе ОС
async def get_release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await ssh_command('cat /etc/os-release')
    await update.message.reply_text(result)

# Функция вывода информации об архитектуре процессора, имени хоста системы и версии ядра
async def get_uname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await ssh_command('uname -a')
    await update.message.reply_text(result)

# Функция вывода информации о времени работы системы
async def get_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await ssh_command('uptime')
    await update.message.reply_text(result)

# Функция вывода информации о состоянии файловой системы
async def get_df(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await ssh_command('df -h')
    await update.message.reply_text(result)

# Функция вывода информации об оперативной памяти
async def get_free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await ssh_command('free -m')
    await update.message.reply_text(result)

# Функция вывода информации о производительности системы
async def get_mpstat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await ssh_command('mpstat')
    await update.message.reply_text(result)

# Функция вывода информации о работающих в системе пользователях
async def get_w(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await ssh_command('w')
    await update.message.reply_text(result)

# Функция вывода информации о последних 10 входах в систему
async def get_auths(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await ssh_command('last -n 10')
    await update.message.reply_text(result)

# Функция вывода информации о последних 5 критических ошибках
async def get_critical(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await ssh_command('journalctl -p crit -n 5')
    await update.message.reply_text(result)

# Функция вывода информации о запущенных процессах
async def get_ps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await ssh_command('ps aux')
    chunk_size = 4096  # Длина сообщения в ТГ
    for i in range(0, len(result), chunk_size):
        await update.message.reply_text(result[i:i+chunk_size])

# Функция вывода информации об используемых службами портах
async def get_ss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await ssh_command('ss -tuln')
    await update.message.reply_text(result)

# Функция вывода информации об установленных пакетах
async def get_apt_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название пакета или введите 'all', чтобы вывести все пакеты:")
    return 'APT_LIST'

# Функция вывода информации об установленных пакетах. А именно обработка выбора пользователя.
async def get_apt_list_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    package_name = update.message.text
    if package_name != 'all':
        result = await ssh_command(f'apt list --installed | grep {package_name}')
    else:
        result = await ssh_command('apt list --installed')

    chunk_size = 4096  # Длина сообщения в ТГ
    for i in range(0, len(result), chunk_size):
        await update.message.reply_text(result[i:i+chunk_size])
    return ConversationHandler.END
    
# Функция вывода информации о запущенных сервисах
async def get_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await ssh_command('systemctl list-units --type=service --state=running')
    chunk_size = 4096  # Длина сообщения в ТГ
    for i in range(0, len(result), chunk_size):
        await update.message.reply_text(result[i:i+chunk_size])

# Функция вывода информации о логах репликации PostgreSQL
async def get_repl_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Выполнение команды для получения логов
        result = subprocess.run(
            ["bash", "-c", f"cat /var/log/postgresql/postgresql.log | grep repl"],
            capture_output=True,
            text=True
        )
        logs = result.stdout
        if logs:
            await update.message.reply_text(f"Логи репликации PostgreSQL:\n{logs}")
        else:
            await update.message.reply_text("Логи не найдены.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при получении логов: {str(e)}")

# Функция подключения к базе данных PostgreSQL  
async def asyncpg_connection(command):
    "Подключение asyncpg к базе данных PostgreSQL"
    connection = None
    result = None
    try:
        connection = await asyncpg.connect(user=DB_USER,
                                    password=DB_PASSWORD,
                                    host=DB_HOST,
                                    port=DB_PORT, 
                                    database=DB_DATABASE)
        result = await connection.fetch(command)
        logging.info("Команда успешно выполнена")
    except Exception as error:
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            await connection.close()
    return result

# Функция вывода информации о почтовых адресах из базы данных
async def get_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await asyncpg_connection("SELECT * FROM emails;")
    if result:
        result_str = "\n".join([str(record) for record in result])
        chunk_size = 4096  # Длина сообщения в ТГ
        for i in range(0, len(result_str), chunk_size):
            await update.message.reply_text(result_str[i:i+chunk_size])
    else:
        await update.message.reply_text("No emails found.")

# Функция вывода информации о телефонных номерах из базы данных
async def get_phone_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await asyncpg_connection("SELECT * FROM numbers;")
    if result:
        result_str = "\n".join([str(record) for record in result])
        chunk_size = 4096  # Длина сообщения в ТГ
        for i in range(0, len(result_str), chunk_size):
            await update.message.reply_text(result_str[i:i+chunk_size])
    else:
        await update.message.reply_text("No emails found.")

# Главная функция
def main():
    application = Application.builder().token(TOKEN).build()

    # Обработчик команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", helpCommand))
    application.add_handler(CommandHandler('get_release', get_release))
    application.add_handler(CommandHandler('get_uname', get_uname))
    application.add_handler(CommandHandler('get_uptime', get_uptime))
    application.add_handler(CommandHandler('get_df', get_df))
    application.add_handler(CommandHandler('get_free', get_free))
    application.add_handler(CommandHandler('get_mpstat', get_mpstat))
    application.add_handler(CommandHandler('get_w', get_w))
    application.add_handler(CommandHandler('get_auths', get_auths))
    application.add_handler(CommandHandler('get_critical', get_critical))
    application.add_handler(CommandHandler('get_ps', get_ps))
    application.add_handler(CommandHandler('get_ss', get_ss))
    application.add_handler(CommandHandler('get_services', get_services)) 
    application.add_handler(CommandHandler('get_repl_logs', get_repl_logs))
    application.add_handler(CommandHandler('get_emails', get_emails))
    application.add_handler(CommandHandler('get_phone_numbers', get_phone_numbers))

    

    Conversation = ConversationHandler(
        entry_points=[
            CommandHandler('find_emails', find_email),
            CommandHandler('find_phone_number', find_phone_number),
            CommandHandler('verify_password', verify_password),
            CommandHandler('get_apt_list', get_apt_list),
            CommandHandler('confirm_save_email', confirm_save_email),
            CommandHandler('confirm_save_phone', confirm_save_phone),
            ],
        states={
            'EMAIL': [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_emails)],
            'PHONE': [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_phone_numbers)],
            'PASSWORD': [MessageHandler(filters.TEXT & ~filters.COMMAND, is_strong_password)],
            'APT_LIST': [MessageHandler(filters.TEXT & ~filters.COMMAND, get_apt_list_choice)],
            'CONFIRM_EMAIL': [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_save_email)],
            'CONFIRM_PHONE': [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_save_phone)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            MessageHandler(filters.COMMAND, cancel)
            ],
    )
    application.add_handler(Conversation) 
    
    # Обработчик текстовых сообщений
          
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Обработчик неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, unknownCommand))

    # Запуск
    application.run_polling()

if __name__ == '__main__':
    main()
