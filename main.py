from telethon import TelegramClient, events, Button
from telethon.utils import get_display_name
from telethon.tl.functions.messages import UpdatePinnedMessageRequest
from telethon.errors import UserNotParticipantError
from telethon.tl.functions.channels import GetParticipantRequest
import time
import speedtest

# ---------------- CREDENTIALS ----------------
api_id = 2852262  # replace
api_hash = "968e06560801f5f264fe33d700329ddd"
bot_token = "8491683377:AAG7m6QtA17P3jH7CpLfor30cIzTwv2Q7oc" # ---------------- GROUP & CHANNEL ----------------
TARGET_GROUP = -1002888180583  # replace with your group id
GROUP_LINK = "https://t.me/+FQ3boB77n805N2Y1"  # replace with actual invite link
TARGET_CHANNEL = -1002577893818
CHANNEL_LINK = "https://t.me/exanic"
client = TelegramClient('ad_bot', api_id, api_hash).start(bot_token=bot_token)

# ---------------- STORAGE ----------------
user_data = {}
post_history = {}

# ---------------- LIMITS ----------------
MAX_POSTS = 7
COOLDOWN = 60 * 60  # 1 hour

# ---------------- MEMBERSHIP CHECKS ----------------
async def is_member(entity_id, user_id):
    try:
        await client(GetParticipantRequest(entity_id, user_id))
        return True
    except UserNotParticipantError:
        return False
    except Exception as e:
        print(f"Membership check error ({entity_id}): {e}")
        return False

async def check_membership(user_id):
    group_member = await is_member(TARGET_GROUP, user_id)
    channel_member = await is_member(TARGET_CHANNEL, user_id)
    return group_member, channel_member

# ---------------- START ----------------
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    user_id = event.sender_id
    await check_and_proceed(user_id)

async def check_and_proceed(user_id, event=None):
    """Check membership for group and channel. If OK, proceed to questions."""
    group_member, channel_member = await check_membership(user_id)

    if not group_member or not channel_member:
        text = "❌ You must join the following to use this bot:\n\n"
        buttons = []

        if not group_member:
            text += "• Group\n"
            buttons.append([Button.url("📢 Join Group", GROUP_LINK)])
        if not channel_member:
            text += "• Channel\n"
            buttons.append([Button.url("📢 Join Channel", CHANNEL_LINK)])

        # Add re-check button
        buttons.append([Button.inline("✅ I've Joined", b"recheck")])

        if event:
            await event.respond(text, buttons=buttons)
        else:
            await client.send_message(user_id, text, buttons=buttons)
        return

    # ✅ User is member of both → continue
    user_data[user_id] = {"step": 0, "answers": {}}
    await ask_question(user_id)

# ---------------- RE-CHECK CALLBACK ----------------
@client.on(events.CallbackQuery(pattern=b"recheck"))
async def recheck_handler(event):
    await event.answer("🔄 Re-checking membership...")
    await check_and_proceed(event.sender_id, event)

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

async def ask_question(user_id):
    step = user_data[user_id]["step"]
    if step < len(questions):
        q = questions[step]

        # ✅ Filter funds source based on rate
        if q["key"] == "source":
            rate = float(user_data[user_id]["answers"].get("rate", 0))
            filtered_buttons = []
            for btn_row in q["buttons"]:
                row = []
                for btn in btn_row:
                    if rate < 100 and btn.data == b"mix":
                        continue
                    if rate > 100 and btn.data == b"legit":
                        continue
                    if rate > 100 and btn.data == b"gaming":
                        continue
                    if rate > 105 and btn.data == b"layer2":
                        continue
                    if rate>105 and btn.data == b"stock":
                        continue
                    row.append(btn)
                if row:
                    filtered_buttons.append(row)
            await client.send_message(user_id, q["question"], buttons=filtered_buttons)

        # ✅ Filter payment method based on rate (block ecom <97 or >105, block cdm >95)
        elif q["key"] == "payment":
            rate = float(user_data[user_id]["answers"].get("rate", 0))
            filtered_buttons = []
            for btn_row in q["buttons"]:
                row = []
                for btn in btn_row:
                    if btn.data == b"ecom" and (rate < 97 or rate > 105):
                        continue
                    if btn.data == b"cdm" and rate > 95:
                        continue
                    if btn.data == b"cardless" and rate > 95:
                        continue
                    row.append(btn)
                if row:
                    filtered_buttons.append(row)
            await client.send_message(user_id, q["question"], buttons=filtered_buttons)

        elif "buttons" in q:
            await client.send_message(user_id, q["question"], buttons=q["buttons"])
        else:
            await client.send_message(user_id, q["question"])
    else:
        await finalize_post(user_id)

# ---------------- CALLBACK HANDLER ----------------
@client.on(events.CallbackQuery)
async def callback_handler(event):
    if event.data == b"recheck":
        return

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
    if not event.is_private:
        return

    user_id = event.sender_id
    if user_id not in user_data:
        return

    step = user_data[user_id]["step"]
    if step >= len(questions):
        return

    q = questions[step]
    key = q["key"]

    # 🚫 If this step has buttons (type, chain, payment, source) block text input
    if "buttons" in q and key not in ["amount", "rate"]:
        await event.respond("❌ Please use the buttons above instead of typing.")
        return

    # ✅ Allow text input ONLY for amount & rate
    value = event.raw_text.strip()

    if key == "amount":
        if not value.isdigit():
            await event.respond("❌ Please enter numbers only for amount.")
            return
        amount = int(value)
        if amount < 1 or amount > 10000:
            await event.respond("❌ Amount must be between 1 and 10000 USDT.")
            return

    if key == "rate":
        try:
            rate = float(value)
        except ValueError:
            await event.respond("❌ Please enter a valid number for rate.")
            return
        if rate < 83 or rate > 115:
            await event.respond("❌ Rate must be between 83 and 115.")
            return

    # ✅ Store valid text input and move to next step
    user_data[user_id]["answers"][key] = value
    user_data[user_id]["step"] += 1
    await ask_question(user_id)

# ---------------- FINAL POST ----------------
async def finalize_post(user_id):
    now = time.time()
    history = post_history.get(user_id, [])

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
        f"Escrow\n"
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
    del user_data[user_id]

print("Bot is running...")
client.run_until_disconnected()
