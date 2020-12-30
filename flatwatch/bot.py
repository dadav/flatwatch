import logging
import re
import threading
from time import sleep
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler,\
    CallbackContext, ConversationHandler, Filters, MessageHandler
from .immo import locations, flat_count
from .db import SqlBackend
from typing import Dict
from datetime import datetime, timedelta
from functools import wraps

log = logging.getLogger('rich')


CHOOSE, MULTICHOICE_CALLBACK = range(2)

RE_PRICE = re.compile(r'(\d+)\s*€')
RE_ROOMS = re.compile(r'(\d+)\s+(?:räume?|rooms)', re.IGNORECASE)
RE_AREA = re.compile(r'(\d+)\s*(?:qm|m|gr[öo]ße?|fläche)', re.IGNORECASE)
RE_RADIUS = re.compile(r'(\d+)\s*km', re.IGNORECASE)

BACKEND = None

SPAM_MEMORY: Dict[str, datetime] = dict()


def is_spam(chatid):
    chatid = str(chatid)

    if chatid not in SPAM_MEMORY:
        SPAM_MEMORY[chatid] = datetime.utcnow()
        return False

    if SPAM_MEMORY[chatid] + timedelta(seconds=5) > datetime.utcnow():
        return True

    SPAM_MEMORY[chatid] = datetime.utcnow()
    return False


def cmd_add(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat.id
    if is_spam(chat_id):
        update.message.reply_text('Hey, hey, don\'t type so fast...')
        return ConversationHandler.END

    user_data = context.user_data
    user_data.clear()
    user_data['params'] = dict()

    given_text = " ".join(update.message.text.split()[1:])

    if not given_text:
        update.message.reply_text('This is not how it works. Give me a location like this: /add <location>')
        return ConversationHandler.END

    possible_locations = locations(given_text)

    if not possible_locations:
        update.message.reply_text('Cant find any informations about this location!!')
        return ConversationHandler.END

    if len(possible_locations) == 1:
        user_data['params']['location'] = possible_locations[0]
        update.message.reply_text('Set location, now give me some filters...')
        return CHOOSE

    user_data['params']['location'] = possible_locations

    options = [[InlineKeyboardButton(name, callback_data=locid)]
               for name, locid in possible_locations]

    reply_markup = InlineKeyboardMarkup(options)
    user_data['choice'] = 'location'
    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return MULTICHOICE_CALLBACK

def cmd_info(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat.id
    if is_spam(chat_id):
        update.message.reply_text('Hey, hey, don\'t type so fast...')
        return CHOOSE
    user_data = context.user_data
    already_given = '\n'.join(['{}: {}'.format(key, value)
                               for key, value in user_data['params'].items()])

    missing = missing_params(user_data['params'])

    if not missing:
        additional = 'Ready to go! Type "/done"'
    else:
        additional = 'You can also set: {}'.format('\n'.join(missing))

    update.message.reply_text(
        'I\'ve already got this information from you:\n{}\n\n{}'.format(already_given, additional))
    return CHOOSE

def cmd_rooms(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat.id
    if is_spam(chat_id):
        update.message.reply_text('Hey, hey, don\'t type so fast...')
        return CHOOSE
    user_data = context.user_data
    given_text = update.message.text

    match = RE_ROOMS.search(given_text)
    if not match:
        update.message.reply_text('Could not extract rooms value...')
        return CHOOSE

    rooms = match.groups()[0]
    user_data['params']['rooms'] = rooms
    update.message.reply_text('Set rooms to {}!'.format(rooms))
    return CHOOSE

def cmd_price(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat.id
    if is_spam(chat_id):
        update.message.reply_text('Hey, hey, don\'t type so fast...')
        return CHOOSE
    user_data = context.user_data
    given_text = update.message.text

    match = RE_PRICE.search(given_text)
    if not match:
        update.message.reply_text('Could not extract price value...')
        return CHOOSE

    price = match.groups()[0]
    user_data['params']['price'] = price
    update.message.reply_text('Set price to {}€!'.format(price))
    return CHOOSE

def cmd_area(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat.id
    if is_spam(chat_id):
        update.message.reply_text('Hey, hey, don\'t type so fast...')
        return CHOOSE
    user_data = context.user_data
    given_text = update.message.text

    match = RE_AREA.search(given_text)

    if not match:
        update.message.reply_text('Could not extract area value...')
        return CHOOSE

    area = match.groups()[0]
    user_data['params']['area'] = area

    update.message.reply_text('Set area to {}m²!'.format(area))
    return CHOOSE

def cmd_list(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    if is_spam(chat_id):
        update.message.reply_text('Hey, hey, don\'t type so fast...')
        return
    entries = BACKEND.load(chat_id)
    if not entries:
        update.message.reply_text('No entries found!')
        return
    txt = list()
    for entry in entries:
        _, _, location, _, price, rooms, area, radius, count = entry
        txt.append('{} ({}€/{}m²/{} rooms/{}km)'.format(location, price, area, rooms, radius))
    update.message.reply_text('\n'.join(txt))

def cmd_del(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat.id
    if is_spam(chat_id):
        update.message.reply_text('Hey, hey, don\'t type so fast...')
        return ConversationHandler.END
    user_data = context.user_data
    entries = BACKEND.load(chat_id)
    if not entries:
        update.message.reply_text('No entries found')
        return ConversationHandler.END

    options = list()
    for entry in entries:
        entryid, _, location, _, price, rooms, area, radius, count = entry
        options.append([InlineKeyboardButton(
            '{} ({}€/{}m²/{} rooms/{}km)'.format(location, price, area, rooms, radius),
            callback_data=entryid)])
    reply_markup = InlineKeyboardMarkup(options)
    user_data['choice'] = 'deletion'
    update.message.reply_text('Which entry do you want to delete?', reply_markup=reply_markup)
    return MULTICHOICE_CALLBACK

def cmd_done(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat.id
    if is_spam(chat_id):
        update.message.reply_text('Hey, hey, don\'t type so fast...')
        return CHOOSE
    user_data = context.user_data
    location, locationid = user_data['params']['location']
    del user_data['params']['location']
    BACKEND.save(chat_id, location, locationid, **user_data['params'])
    user_data.clear()
    return ConversationHandler.END

def cmd_radius(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat.id
    if is_spam(chat_id):
        update.message.reply_text('Hey, hey, don\'t type so fast...')
        return CHOOSE

    user_data = context.user_data
    given_text = update.message.text

    match = RE_RADIUS.search(given_text)

    if not match:
        update.message.reply_text('Could not extract radius value...')
        return CHOOSE

    radius = match.groups()[0]
    user_data['params']['radius'] = radius
    update.message.reply_text('Set radius to {}km!'.format(radius))
    return CHOOSE

def missing_params(given):
    possible = {'price', 'area', 'location', 'radius', 'rooms'}
    return possible - set(given.keys())

def multichoice_callback(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    query = update.callback_query
    query.answer()
    if user_data['choice'] == 'location':
        user_data['params']['location'] = [(name, locid) for name, locid in user_data['params']['location']
                                            if query.data == locid][0]
        query.edit_message_text(text='Set location, now give me some filters...')
    elif user_data['choice'] == 'deletion':
        chat_id = query.message.chat.id
        BACKEND.delete(chat_id, int(query.data))
        query.edit_message_text(text='Deleted the selected entry!')
        return ConversationHandler.END
    return CHOOSE

def cancel(update: Update, context: CallbackContext) -> None:
    context.user_data.clear()
    update.message.reply_text('Bye')

def cmd_help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('''Use /add <location> to enter the input-mode. Now \
you can write stuff like "only 500€" or "min 80qm" or "around 20km" or "3 rooms" to set \
some filters. If you are done, type /done. If you want tot see the already given data, type /info. \
You can use /list to show the already tracked items. With /del you can delete items. \
Use /cancel if you want to dismiss the already given data.
''')

def fetcher(updater: Updater, backend: SqlBackend, config: Dict):
    while True:
        for entry in backend.load():
            entryid, chat_id, location, locationid, price, rooms, area, radius, count = entry
            try:
                current_flats = flat_count(location, locationid, price, rooms, area, radius)
            except Exception as count_err:
                log.debug(count_err)
                continue
            if count == -1:
                # first lookup
                backend.set_count(entryid, current_flats)
            elif current_flats != count:
                inc_dec = 'increased' if current_flats > count else 'decreased'
                updater.bot.send_message(chat_id, 'ALERT! The flatcount for {} {} from {} to {}'.format(
                    "{} ({}€/{}m²/{} rooms)".format(location, price, area, rooms), inc_dec, count, current_flats))
                backend.set_count(entryid, current_flats)
            sleep(0.5)
        sleep(config['fetcher']['interval'])


def start(token: str, backend: SqlBackend, config: Dict):
    global BACKEND

    BACKEND = backend

    updater = Updater(token, use_context=True)
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('add', cmd_add),
        ],
        states={
            CHOOSE: [
                MessageHandler(Filters.regex(RE_PRICE), cmd_price),
                MessageHandler(Filters.regex(RE_ROOMS), cmd_rooms),
                MessageHandler(Filters.regex(RE_AREA), cmd_area),
                MessageHandler(Filters.regex(RE_RADIUS), cmd_radius),
                CommandHandler('info', cmd_info),
                CommandHandler('done', cmd_done),
            ],
            MULTICHOICE_CALLBACK: [CallbackQueryHandler(multichoice_callback)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    conv_handler2 = ConversationHandler(
        entry_points=[
            CommandHandler('del', cmd_del),
        ],
        states={
            MULTICHOICE_CALLBACK: [CallbackQueryHandler(multichoice_callback)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # add commands
    updater.dispatcher.add_handler(conv_handler)
    updater.dispatcher.add_handler(conv_handler2)
    updater.dispatcher.add_handler(CommandHandler('list', cmd_list))
    updater.dispatcher.add_handler(CommandHandler('help', cmd_help))

    # Start the Bot
    updater.start_polling()

    th = threading.Thread(target=fetcher, args=(updater, backend, config,))
    th.start()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()
