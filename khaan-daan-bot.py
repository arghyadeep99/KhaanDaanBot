import telegram
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
						  ConversationHandler)
from googlemaps import Client as GoogleMaps
import os
import logging

PORT = int(os.environ.get('PORT', 5000))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					level=logging.INFO, filename='khaandaan-bot.log', filemode='a')

logger = logging.getLogger(__name__)

LOCATION, PHOTO, DIET, SERVINGS, TIME, CONFIRMATION = range(6)

reply_keyboard = [['Confirm', 'Restart']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)

TOKEN = 'Your_Bot_Token_Goes_Here'
bot = telegram.Bot(token=TOKEN)

chat_id = "@YOURCHANNELNAME"

GMAPS_TOKEN = 'Your Geocoding API goes here '
gmaps = GoogleMaps(GMAPS_TOKEN)


def facts_to_str(user_data):
	facts = list()

	for key, value in user_data.items():
		facts.append('{} - {}'.format(key, value))

	return "\n".join(facts).join(['\n', '\n'])


def start(update, context):
	update.message.reply_text(
		"Namaste, Welcome to Khaan-Daan! I will assist you in managing your leftover food. To start, please type the location of your food.")
	return LOCATION


def location(update, context):
	user = update.message.from_user
	user_data = context.user_data
	category = 'Location'
	text = update.message.text
	user_data[category] = text
	logger.info("Location of %s: %s", user.first_name, update.message.text)

	update.message.reply_text("Oh, that's nice. Now, please upload an image of the leftover food, or send /skip if you don't want to.")
	return PHOTO


def photo(update, context):
	user = update.message.from_user
	user_data = context.user_data
	photo_file = update.message.photo[-1].get_file()
	photo_file.download('user_photo.jpg')
	category = 'Photo Provided'
	user_data[category] = 'Yes'
	logger.info("Photo of %s: %s", user.first_name, 'user_photo.jpg')
	update.message.reply_text("Okay, that looks yummy! Can you please specify the food details (Food Name - Veg/Non-Veg)?")

	return DIET


def skip_photo(update, context):
	user = update.message.from_user
	user_data = context.user_data
	category = 'Photo Provided'
	user_data[category] = 'No'
	logger.info("User %s did not send a photo.", user.first_name)
	update.message.reply_text("Nevermind, we understand. Can you please specify the food details (Food Name - Veg/Non-Veg)?")

	return DIET


def diet(update, context):
	user = update.message.from_user
	user_data = context.user_data
	category = 'Food Details'
	text = update.message.text
	user_data[category] = text
	logger.info("Dietary Specification of food: %s", update.message.text)
	update.message.reply_text("How many people can be served approximately?")

	return SERVINGS

def servings(update, context):
	user = update.message.from_user
	user_data = context.user_data
	category = 'Approximate Servings'
	text = update.message.text
	user_data[category] = text
	logger.info("Number of servings: %s", update.message.text)
	update.message.reply_text("Deadline to collect the food?")

	return TIME
	
def time(update, context):
	user = update.message.from_user
	user_data = context.user_data
	category = 'Food Collection Deadline'
	text = update.message.text
	user_data[category] = text
	logger.info("Time to Take Food By: %s", update.message.text)
	update.message.reply_text("Thank you for providing me the info! Please check if the info is correct:"
								"{}".format(facts_to_str(user_data)), reply_markup=markup)

	return CONFIRMATION

def confirmation(update, context):
	user_data = context.user_data
	user = update.message.from_user
	update.message.reply_text(f"Thank you! I will post this on the channel {chat_id} now.", reply_markup=ReplyKeyboardRemove())
	if (user_data['Photo Provided'] == 'Yes'):
		del user_data['Photo Provided']
		bot.send_photo(chat_id=chat_id, photo=open('user_photo.jpg', 'rb'), 
		caption="<b>Khaana milrela hai bhailog!!</b> Check the details below: \n {}".format(facts_to_str(user_data)) +
		"\n For more information, message the poster {}".format(user.name), parse_mode='html')
	else:
		del user_data['Photo Provided']
		bot.sendMessage(chat_id=chat_id, 
			text="<b>Picture nahi hua toh kya? Khaana milrela hai bhailog!!</b> Check the details below: \n {}".format(facts_to_str(user_data)) +
		"\n For more information, please message {}".format(user.name), parse_mode='html')
	geocode_result = gmaps.geocode(user_data['Location'])
	lat = geocode_result[0]['geometry']['location'] ['lat']
	lng = geocode_result[0]['geometry']['location']['lng']
	bot.sendLocation(chat_id=chat_id, latitude=lat, longitude=lng)
	return ConversationHandler.END

def cancel(update, context):
	user = update.message.from_user
	logger.info("User %s canceled the conversation.", user.first_name)
	update.message.reply_text('Bye! Hope to see you again next time.',
							  reply_markup=ReplyKeyboardRemove())

	return ConversationHandler.END


def error(update, context):
	"""Log Errors caused by Updates."""
	logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():

	updater = Updater(TOKEN, use_context=True)

	# Get the dispatcher to register handlers
	dp = updater.dispatcher

	# Add conversation handler with the states LOCATION, PHOTO, DIET, SERVINGS, TIME, CONFIRMATION
	conv_handler = ConversationHandler(
		entry_points=[CommandHandler('start', start)],

		states={

			LOCATION: [CommandHandler('start', start), MessageHandler(Filters.text, location)],

			PHOTO: [CommandHandler('start', start), MessageHandler(Filters.photo, photo),
					CommandHandler('skip', skip_photo)],

			DIET: [CommandHandler('start', start), MessageHandler(Filters.text, diet)],

			SERVINGS: [CommandHandler('start', start), MessageHandler(Filters.text, servings)],

			TIME: [CommandHandler('start', start), MessageHandler(Filters.text, time)],

			CONFIRMATION: [MessageHandler(Filters.regex('^Confirm$'),
									  confirmation),
			MessageHandler(Filters.regex('^Restart$'),
									  start)
					   ]

		},

		fallbacks=[CommandHandler('cancel', cancel)]
	)

	dp.add_handler(conv_handler)

	# log all errors
	dp.add_error_handler(error)

	#updater.start_polling()
	updater.start_webhook(listen="0.0.0.0", port=int(PORT), url_path=TOKEN)
	updater.bot.setWebhook('https://YOUR-APP-NAME.herokuapp.com/' + TOKEN)

	updater.idle()


if __name__ == '__main__':
	main()
