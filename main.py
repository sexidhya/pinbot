from telethon import TelegramClient, events, Button
from telethon.utils import get_display_name
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
import time
import speedtest

# Credentials
api_id = 2852262  # replace
api_hash = "968e06560801f5f264fe33d700329ddd"
bot_token = "8491683377:AAG7m6QtA17P3jH7CpLfor30cIzTwv2Q7oc"
TARGET_GROUP = -1002888180583  # replace with your group id

client = TelegramClient('ad_bot', api_id, api_hash).start(bot_token=bot_token)

# Storage
user_data = {}
post_history = {}  # {user_id: [timestamps]}

# Limits
MAX_POSTS = 7
COOLDOWN = 30 * 60  # 30 minutes in seconds

# ---------------- PING COMMAND ----------------
@client.on(events.NewMessage(pattern="/ping"))
async def ping_handler(event):
    start = time.time()
    msg = await event.respond("🏓 Pinging...")
    latency = round((time.time() - start) * 1000, 2)

    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download = round(st.download() / 1_000_000, 2)
        upload = round(st.upload() / 1_000_000, 2)
    except Exception:
        download = upload = "Error"

    await msg.edit(
        f"✅ **Pong!**\n"
        f"⏱ Response Time: `{latency} ms`\n"
        f"📡 Download: `{download} Mbps`\n"
        f"📤 Upload: `{upload} Mbps`"
    )

# ---------------- QUESTIONS ----------------
questions = [
    {"key": "type", "question": "Are you Selling or Buying?",
     "buttons": [[Button.inline("Selling", b"selling")],
                 [Button.inline("Buying", b"buying")]]},
    {"key": "amount", "question": "Enter the amount of USDT (Only Numbers, no $):"},
    {"key": "chain", "question": "Select the Crypto Chain:",
     "buttons": [[Button.inline("BEP20", b"bep20")],
                 [Button.inline("TRC20", b"trc20")],
                 [Button.inline("POLYGON", b"polygon")],
                 [Button.inline("ERC20", b"erc20")]]},
    {"key": "rate", "question": "Enter the Rate (e.g. 85.5):"},
    {"key": "payment", "question": "Select the Payment Method:",
     "buttons": [[Button.inline("UPI/IMPS", b"upi")],
                 [Button.inline("CDM", b"cdm")],
                 [Button.inline("Cardless", b"cardless")],
                 [Button.inline("IMPS/RTGS", b"imps")],
                 [Button.inline("Ecom", b"ecom")]]},
    {"key": "source", "question": "Select the Funds Source:",
     "buttons": [[Button.inline("Legit", b"legit")],
                 [Button.inline("Stock", b"stock")],
                 [Button.inline("Mix", b"mix")],
                 [Button.inline("Layer2", b"layer2")],
                 [Button.inline("Gaming", b"gaming")]]}
]

# ---------------- START ----------------
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    user_data[event.sender_id] = {"step": 0, "answers": {}}
    await ask_question(event.sender_id)

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

# ---------------- CALLBACK HANDLER ----------------
@client.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    step = user_data.get(user_id, {}).get("step")

    if step is None:
        return

    choice = event.data.decode()

    if step < len(questions) and "buttons" in questions[step]:
        key = questions[step]["key"]
        user_data[user_id]["answers"][key] = choice.capitalize()
        user_data[user_id]["step"] += 1
        await event.answer(f"You chose {choice.capitalize()}")
        await ask_question(user_id)

# ---------------- TEXT INPUT HANDLER ----------------
@client.on(events.NewMessage)
async def handle_answers(event):
    if event.is_private and event.sender_id in user_data:
        step = user_data[event.sender_id]["step"]

        if step < len(questions) and "buttons" in questions[step]:
            return

        if step < len(questions):
            key = questions[step]["key"]
            value = event.raw_text.strip()

            # Validation
            if key == "amount" and not value.isdigit():
                await event.respond("❌ Please enter numbers only for amount.")
                return
            if key == "rate":
                try:
                    float(value)
                except ValueError:
                    await event.respond("❌ Please enter a valid number for rate.")
                    return

            user_data[event.sender_id]["answers"][key] = value
            user_data[event.sender_id]["step"] += 1
            await ask_question(event.sender_id)

# ---------------- FINAL POST ----------------
async def finalize_post(user_id):
    now = time.time()
    history = post_history.get(user_id, [])

    # Check post count
    if len(history) >= MAX_POSTS:
        await client.send_message(user_id, "❌ You have reached the maximum of 7 posts.")
        del user_data[user_id]
        return

    # Check cooldown
    if history and now - history[-1] < COOLDOWN:
        remaining = int((COOLDOWN - (now - history[-1])) / 60)
        await client.send_message(user_id, f"⏳ Please wait {remaining} minutes before posting again.")
        del user_data[user_id]
        return

    data = user_data[user_id]["answers"]
    entity = await client.get_entity(user_id)

    if entity.username:
        dm_text = f"@{entity.username}"
    else:
        dm_text = f"[{get_display_name(entity)}](tg://user?id={user_id})"

    msg = (
        f"#{data['type']}\n"
        f"Rate: {data['rate']}\n"
        f"Quantity: ${data['amount']}\n"
        f"Crypto Chain: {data['chain']}\n"
        f"Payment Method: {data['payment']}\n"
        f"Funds Source: {data['source']}\n"
        f"Escrow via @Exanic\n"
        f"**DM: {dm_text}**"
    )

    post = await client.send_message(TARGET_GROUP, msg)
    await client(UpdatePinnedMessageRequest(
        peer=TARGET_GROUP,
        id=post.id,
        silent=True
    ))
    await client.send_message(user_id, "✅ Your advertisement has been posted and pinned!")

    history.append(now)
    post_history[user_id] = history[-MAX_POSTS:]
    del user_data[user_id]

print("Bot is running...")
client.run_until_disconnected()
