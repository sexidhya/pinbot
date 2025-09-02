from telethon import TelegramClient, events, Button
from telethon.utils import get_display_name

# Credentials remain unchanged
api_id = 123456  # replace
api_hash = "your_api_hash"
bot_token = "8491683377:AAG7m6QtA17P3jH7CpLfor30cIzTwv2Q7oc"
TARGET_GROUP = -1002888180583  # replace with your group id

client = TelegramClient('ad_bot', api_id, api_hash).start(bot_token=bot_token)

user_data = {}

# Stepwise questions
questions = [
    {"key": "type", "question": "Are you Selling or Buying?", 
     "buttons": [Button.inline("Selling", b"selling"), Button.inline("Buying", b"buying")]},
    {"key": "amount", "question": "Enter the amount of USDT(Don't use $ , Only Numbers):"},
    {"key": "chain", "question": "Enter the Crypto Chain (e.g. TRC20, BEP20):"},
    {"key": "rate", "question": "Enter the Rate (e.g. 85.5):"},
    {"key": "payment", "question": "Enter the Payment Method (e.g. UPI, CDM , Cardless):"},
    {"key": "source", "question": "Enter the Funds Source:"}
]

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

# Handle Selling/Buying button clicks
@client.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    step = user_data.get(user_id, {}).get("step")
    if step == 0:  # only first step
        choice = event.data.decode()
        user_data[user_id]["answers"]["type"] = choice.capitalize()
        user_data[user_id]["step"] += 1
        await event.answer(f"You chose {choice.capitalize()}")
        await ask_question(user_id)

# Handle text input for other steps
@client.on(events.NewMessage)
async def handle_answers(event):
    if event.is_private and event.sender_id in user_data:
        step = user_data[event.sender_id]["step"]
        # Wait for Selling/Buying button if step 0
        if step < len(questions) and "buttons" in questions[step]:
            return

        if step < len(questions):
            key = questions[step]["key"]
            user_data[event.sender_id]["answers"][key] = event.raw_text.strip()
            user_data[event.sender_id]["step"] += 1
            await ask_question(event.sender_id)

async def finalize_post(user_id):
    data = user_data[user_id]["answers"]
    entity = await client.get_entity(user_id)

    # DM field logic
    if entity.username:
        dm_text = f"@{entity.username}"
    else:
        name = get_display_name(entity)
        dm_text = f"[{name}](tg://user?id={user_id})"

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
    await client.pin_message(TARGET_GROUP, post, notify=False)
    await client.send_message(user_id, "✅ Your advertisement has been posted and pinned!")
    del user_data[user_id]

print("Bot is running...")
client.run_until_disconnected()
