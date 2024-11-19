import telebot
import mysql.connector
from mysql.connector import Error
import requests

# Remplacez par votre token Telegram
TOKEN = '7734765252:AAG1zYgVpKJZlMh5TWS1frHRYin0a6Fq3Z4'
bot = telebot.TeleBot(TOKEN)

# Connexion à la base de données
def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='ImageDB',
            connection_timeout=180,
            autocommit=True
        )
        if connection.is_connected():
            print("✅ Connexion à la base de données réussie.")
            return connection
        else:
            print("❌ La connexion à la base de données a échoué.")
            return None
    except Error as e:
        print(f"Erreur lors de la tentative de connexion : {e}")
        return None

# Commande de démarrage pour afficher le menu d'aide
@bot.message_handler(commands=['start'])
def send_welcome(message):
    help_text = (
        "👋 Bienvenue sur le bot de gestion d'images !\n"
        "Voici les commandes disponibles :\n\n"
        "📤 /upload - Envoyez une image pour l'uploader dans la base de données.\n"
        "🔍 /search - Affiche toutes les images uploadées avec leurs ID et permet d'en sélectionner une.\n"
        "❌ /cancel - Annule la recherche en cours sur le robot sans supprimer l'image de la base de données.\n"
        "\n💡 Astuce : Utilisez ces commandes pour gérer vos images et interagir avec votre robot ESP32-CAM."
    )
    bot.send_message(message.chat.id, help_text)


# Commande pour uploader une image
@bot.message_handler(commands=['upload'])
def upload_image(message):
    bot.send_message(message.chat.id, "Veuillez envoyer l'image que vous souhaitez uploader.")

    @bot.message_handler(content_types=['photo'])
    def handle_image(received_message):
        connection = create_connection()
        cursor = connection.cursor()

        # Récupérer l'image
        file_info = bot.get_file(received_message.photo[-1].file_id)
        file = requests.get(f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}')
        
        # Sauvegarder dans la base de données
        image_name = f"{received_message.photo[-1].file_id}.jpg"
        image_data = file.content

        try:
            cursor.execute("INSERT INTO images (image_name, image_data) VALUES (%s, %s)", (image_name, image_data))
            connection.commit()
            bot.send_message(received_message.chat.id, "Image uploadée avec succès !")
        except Error as e:
            bot.send_message(received_message.chat.id, f"Erreur lors de l'upload : {e}")
        finally:
            cursor.close()
            connection.close()

# Commande pour afficher les images
@bot.message_handler(commands=['search'])
def list_images(message):
    connection = create_connection()

    # Vérification de la connexion
    if connection is None:
        bot.send_message(message.chat.id, "❌ Impossible de se connecter à la base de données.")
        return

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id, image_name, image_data, date_uploaded FROM images")
        results = cursor.fetchall()

        if results:
            bot.send_message(message.chat.id, "🔍 Images disponibles :")

            # Afficher toutes les images disponibles avec leur ID
            for row in results:
                image_id = row[0]
                image_name = row[1]
                image_data = row[2]
                date_uploaded = row[3]

                bot.send_photo(
                    message.chat.id,
                    photo=image_data,
                    caption=f"ID: {image_id}\nDate: {date_uploaded}"
                )

            bot.send_message(
                message.chat.id,
                "✏️ Envoyez l'ID de l'image à charger sur le robot pour continuer."
            )

            # On attend maintenant la saisie d'un ID d'image
            @bot.message_handler(func=lambda message: message.text.isdigit())
            def show_image_by_id(message):
                image_id = int(message.text)
                connection = create_connection()

                if connection is None:
                    bot.send_message(message.chat.id, "❌ Impossible de se connecter à la base de données.")
                    return

                try:
                    cursor = connection.cursor()
                    cursor.execute("SELECT image_name, image_data, date_uploaded FROM images WHERE id = %s", (image_id,))
                    result = cursor.fetchone()

                    if result:
                        image_name = result[0]
                        image_data = result[1]
                        date_uploaded = result[2]

                        # Afficher l'image et ses détails
                        bot.send_photo(
                            message.chat.id,
                            photo=image_data,
                            caption=f"✅ Vous avez choisi l'image d'ID {image_id}\n"
                                    f"📅 Date d'enregistrement : {date_uploaded}"
                        )
                    else:
                        bot.send_message(message.chat.id, f"⚠️ Aucune image trouvée avec l'ID {image_id}.")

                except Exception as e:
                    bot.send_message(message.chat.id, f"❌ Erreur lors de la récupération de l'image : {e}")

                finally:
                    if cursor:
                        cursor.close()
                    if connection and connection.is_connected():
                        connection.close()

        else:
            bot.send_message(message.chat.id, "⚠️ Aucune image disponible.")

    except Error as e:
        bot.send_message(message.chat.id, f"❌ Erreur lors de la recherche : {e}")

    finally:
        # Fermeture du curseur et de la connexion
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


# Fonction pour envoyer une image à l'ESP32-CAM
def send_to_robot(image_data):
    try:
        url = "http://192.168.1.100/upload"  # Adresse IP de l'ESP32-CAM
        files = {'file': image_data}
        response = requests.post(url, files=files)
        return response.status_code == 200
    except Exception as e:
        print(f"Erreur : {e}")
        return False

# Commande pour annuler la recherche
@bot.message_handler(commands=['cancel'])
def cancel_search(message):
    bot.send_message(message.chat.id, "Recherche annulée.")
    # Logique pour annuler le processus sur le robot (si nécessaire)
    requests.get("http://192.168.1.100/cancel")  # URL pour annuler la recherche

bot.polling()
