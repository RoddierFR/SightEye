import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import io

# Remplacez par votre token de bot Telegram
TELEGRAM_TOKEN = '7734765252:AAG1zYgVpKJZlMh5TWS1frHRYin0a6Fq3Z4'
# Remplacez par l'adresse IP de votre ESP32 (ex. : 'http://192.168.1.100/upload')
ESP32_URL = 'http://IP_DE_VOTRE_ESP32/upload'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envoyez-moi une photo, et je la transmettrai au robot. Utilisez /stop pour supprimer l'image.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]  # Récupérer la meilleure résolution de l'image
    photo_file = await context.bot.get_file(photo.file_id)
    photo_data = io.BytesIO()
    await photo_file.download(out=photo_data)
    photo_data.seek(0)  # Remettre le curseur du fichier au début

    # Envoyer la photo à l'ESP32
    files = {'file': ('photo.jpg', photo_data, 'image/jpeg')}
    response = requests.post(ESP32_URL, files=files)

    if response.status_code == 200:
        await update.message.reply_text("Photo envoyée au robot avec succès !")
    else:
        await update.message.reply_text("Échec de l'envoi de la photo au robot.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Envoyer une requête DELETE à l'ESP32 pour supprimer l'image
    response = requests.delete(ESP32_URL)

    if response.status_code == 200:
        await update.message.reply_text("Image supprimée du robot avec succès !")
    else:
        await update.message.reply_text("Échec de la suppression de l'image du robot.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CommandHandler("stop", stop))

    application.run_polling()

if __name__ == '__main__':
    main()
