import threading
import telebot
from flask import Flask, request, render_template_string, redirect, url_for, flash
import sqlite3
import os

# Настройка токена бота (убедитесь, что он правильный и содержит двоеточие)
API_TOKEN = "7379196125:AAFD7J-KtaXMeBAe7Tzwske85fC-4oOT7hY"  # замените на ваш токен
bot = telebot.TeleBot(API_TOKEN)

# Инициализация базы данных подписчиков
def init_db():
    conn = sqlite3.connect("subscribers.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

def add_subscriber(user_id):
    conn = sqlite3.connect("subscribers.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# Обработчик команды /start для бота
@bot.message_handler(commands=['start'])
def handle_start(message):
    add_subscriber(message.from_user.id)
    bot.reply_to(message, "Привет! Вы успешно подписались на фразу дня.")

def run_bot():
    init_db()
    bot.polling(none_stop=True)

# Flask-приложение (админка)
app = Flask(__name__)
app.secret_key = "YOUR_SECRET_KEY"  # замените на вашу секретную строку

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_subscribers():
    conn = sqlite3.connect("subscribers.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM subscribers")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        message_text = request.form.get("message")
        image_file = request.files.get("image")
        image_path = None
        if image_file and image_file.filename != "":
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
            image_file.save(image_path)
        subscribers = get_subscribers()
        for user_id in subscribers:
            try:
                if image_path:
                    if message_text:
                        bot.send_photo(user_id, photo=open(image_path, 'rb'), caption=message_text)
                    else:
                        bot.send_photo(user_id, photo=open(image_path, 'rb'))
                else:
                    bot.send_message(user_id, message_text)
            except Exception as e:
                print(f"Ошибка при отправке пользователю {user_id}: {e}")
        if image_path:
            os.remove(image_path)  # удаляем файл после рассылки
        flash("Рассылка отправлена!")
        return redirect(url_for("index"))

    # Шаблон страницы с использованием Bootstrap
    template = '''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
      <title>Админка фразы дня</title>
      <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    </head>
    <body>
      <div class="container mt-5">
        <h1 class="mb-4">Рассылка фразы дня</h1>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="alert alert-success" role="alert">
              {% for msg in messages %}
                {{ msg }}<br>
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        <form method="post" enctype="multipart/form-data">
          <div class="form-group">
            <label for="message">Сообщение для рассылки</label>
            <textarea class="form-control" id="message" name="message" rows="3" placeholder="Введите текст сообщения"></textarea>
          </div>
          <div class="form-group">
            <label for="image">Изображение (необязательно)</label>
            <input type="file" class="form-control-file" id="image" name="image">
          </div>
          <button type="submit" class="btn btn-primary">Отправить рассылку</button>
        </form>
      </div>
      <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.2/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''
    return render_template_string(template)

if __name__ == "__main__":
    # Запускаем бот в отдельном потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    # Запускаем Flask-сервер (админку)
    app.run(host="0.0.0.0", port=5001)