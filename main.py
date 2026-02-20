from telethon import TelegramClient, events, Button
from telethon.utils import get_display_name
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from telethon.errors import UserNotParticipantError
from telethon.tl.functions.channels import GetParticipantRequest
import time
import speedtest

# ---------------- CREDENTIALS ----------------
api_id = 2852262
api_hash = "968e06560801f5f264fe33d700329ddd"
bot_token = "8491683377:AAG7m6QtA17P3jH7CpLfor30cIzTwv2Q7oc"

# ---------------- GROUP & CHANNEL ----------------
TARGET_GROUP = -1002888180583
GROUP_LINK = "https://t.me/+FQ3boB77n805N2Y1"
TARGET_CHANNEL = -1002184803172
CHANNEL_LINK = "https://t.me/exanic"

client = TelegramClient("ad_bot", api_id, api_hash).start(bot_token=bot_token)

# ---------------- STORAGE ----------------
user_data = {}
post_history = {}

# ---------------- LIMITS ----------------
COOLDOWN = 60 * 60  # 1 hour

# ---------------- MEMBERSHIP CHECK ----------------
async def is_member(entity_id, user_id):
    try:
        await client(GetParticipantRequest(entity_id, user_id))
        return True
    except UserNotParticipantError:
        return False
    except Exception:
        return False

async def check_membership(user_id):
    return (
        await is_member(TARGET_GROUP, user_id),
        await is_member(TARGET_CHANNEL, user_id)
    )

# ---------------- START ----------------
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await check_and_proceed(event.sender_id)

async def check_and_proceed(user_id, event=None):
    group_member, channel_member = await check_membership(user_id)

    if not group_member or not channel_member:
        text = "❌ You must join both to use this bot:\n\n"
        buttons = []

        if not group_member:
            text += "• Group\n"
            buttons.append([Button.url("📢 Join Group", GROUP_LINK)])
        if not channel_member:
            text += "• Channel\n"
            buttons.append([Button.url("📢 Join Channel", CHANNEL_LINK)])

        buttons.append([Button.inline("✅ I've Joined", b"recheck")])

        if event:
            await event.respond(text, buttons=buttons)
        else:
            await client.send_message(user_id, text, buttons=buttons)
        return

    user_data[user_id] = {"step": 0, "answers": {}}
    await ask_question(user_id)

# ---------------- RECHECK ----------------
@client.on(events.CallbackQuery(pattern=b"recheck"))
async def recheck(event):
    await event.answer("Re-checking...")
    await check_and_proceed(event.sender_id, event)

# ---------------- QUESTIONS ----------------
questions = [
    {
        "key": "type",
        "question": "Are you Selling or Buying?",
        "buttons": [
            [Button.inline("Selling", b"selling")],
            [Button.inline("Buying", b"buying")]
        ]
    },
    {"key": "amount", "question": "Enter USDT amount (numbers only):"},
    {
        "key": "chain",
        "question": "Select Crypto Chain:",
        "buttons": [
            [Button.inline("BEP20", b"bep20")],
            [Button.inline("TRC20", b"trc20")],
            [Button.inline("POLYGON", b"polygon")],
            [Button.inline("ERC20", b"erc20")]
        ]
    },
    {"key": "rate", "question": "Enter Rate (e.g. 85.5):"},
    {
        "key": "payment",
        "question": "Select Payment Method:",
        "buttons": [
            [Button.inline("UPI / IMPS", b"upi")],
            [Button.inline("CDM", b"cdm")],
            [Button.inline("Cardless", b"cardless")],
            [Button.inline("IMPS / RTGS", b"imps")],
            [Button.inline("Ecom", b"ecom")]
        ]
    },
    {
        "key": "source",
        "question": "Select Funds Source:",
        "buttons": [
            [Button.inline("Legit", b"legit")],
            [Button.inline("Mix", b"mix")],
            [Button.inline("Stock", b"stock")],
            [Button.inline("Layer2", b"layer2")],
            [Button.inline("Gaming", b"gaming")]
        ]
    }
]

async def ask_question(user_id):
    step = user_data[user_id]["step"]
    if step < len(questions):
        q = questions[step]
        if "buttons" in q:
            await client.send_message(user_id, q["question"], buttons=q["buttons"])
        else:
            await client.send_message(user_id, q["question"])
    else:
        await finalize_post(user_id)

# ---------------- CALLBACK ----------------
@client.on(events.CallbackQuery)
async def callbacks(event):
    if event.data == b"recheck":
        return

    user_id = event.sender_id
    if user_id not in user_data:
        return

    step = user_data[user_id]["step"]
    q = questions[step]

    if "buttons" not in q:
        return

    choice = event.data.decode()
    user_data[user_id]["answers"][q["key"]] = choice.capitalize()
    user_data[user_id]["step"] += 1
    await event.answer(choice.capitalize())
    await ask_question(user_id)

# ---------------- TEXT INPUT ----------------
@client.on(events.NewMessage)
async def text_input(event):
    if not event.is_private:
        return

    user_id = event.sender_id
    if user_id not in user_data:
        return

    step = user_data[user_id]["step"]
    q = questions[step]

    if "buttons" in q:
        await event.respond("❌ Use buttons above.")
        return

    value = event.raw_text.strip()

    if q["key"] == "amount":
        if not value.isdigit() or not (1 <= int(value) <= 10000):
            await event.respond("❌ Amount must be 1–10000.")
            return

    if q["key"] == "rate":
        try:
            r = float(value)
            if r < 83 or r > 115:
                raise ValueError
        except:
            await event.respond("❌ Rate must be 83–115.")
            return

    user_data[user_id]["answers"][q["key"]] = value
    user_data[user_id]["step"] += 1
    await ask_question(user_id)

# ---------------- FINAL POST ----------------
async def finalize_post(user_id):
    now = time.time()
    history = post_history.get(user_id, [])

    if history and now - history[-1] < COOLDOWN:
        await client.send_message(user_id, "⏳ Please wait before posting again.")
        del user_data[user_id]
        return

    data = user_data[user_id]["answers"]
    entity = await client.get_entity(user_id)

    # 🔹 PRESERVE dm_text
    if entity.username:
        dm_text = f"@{entity.username}"
        dm_link = f"https://t.me/{entity.username}"
    else:
        dm_text = f"[{get_display_name(entity)}](tg://user?id={user_id})"
        dm_link = f"tg://user?id={user_id}"

    msg = (
        f"#{data['type']}\n"
        f"Rate: {data['rate']}\n"
        f"Quantity: ${data['amount']}\n"
        f"Chain: {data['chain']}\n"
        f"Payment: {data['payment']}\n"
        f"Source: {data['source']}\n"
        f"Escrow via @Exanic\n"
        f"**DM: {dm_text}**"
    )

    buttons = [[Button.url("💬Message Me", dm_link)]]

    post = await client.send_message(
        TARGET_GROUP,
        msg,
        buttons=buttons,
        link_preview=False
    )

    await client(UpdatePinnedMessageRequest(
        peer=TARGET_GROUP,
        id=post.id,
        silent=True
    ))

    await client.send_message(user_id, "✅ Ad posted & pinned successfully!")
    history.append(now)
    post_history[user_id] = history
    del user_data[user_id]

print("Bot is running...")
client.run_until_disconnected()
