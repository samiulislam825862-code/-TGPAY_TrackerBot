import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ChatMemberHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.getenv("CHANNEL_ID", "@TGPay_Offical")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

stats = {
    "posts": 0,
    "joins": 0,
    "leaves": 0,
}

invite_stats = {}
wallet_answers = {}

WALLET_OPTIONS = [
    ("Nagad Agent", "納加德特工"),
    ("bKash Agent", "bKash代理"),
    ("Nagad Personal Wallets", "Nagad個人錢包"),
    ("bKash Personal Wallets", "bKash個人錢包"),
]
async def wallet_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(
            f"{english} — {chinese}",
            callback_data=f"wallet_{i}"
        )]
        for i, (english, chinese) in enumerate(WALLET_OPTIONS)
    ]

    await update.message.reply_text(
        "❓ What kind of wallet do you have?\n"
        "你用的是哪種錢包？",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def wallet_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    index = int(query.data.split("_")[1])
    english, chinese = WALLET_OPTIONS[index]

    user = query.from_user

    wallet_answers[user.id] = {
        "name": user.full_name,
        "username": user.username,
        "wallet": english,
        "wallet_chinese": chinese,
    }
    await query.edit_message_text(
        "✅ Selection recorded.\n"
        "已記錄您的選擇。\n\n"
        f"💳 {english}\n"
        f"💳 {chinese}\n\n"
        "❓ Why should you work for our company?\n"
        "為什麼要加入我們公司？"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "💰 High Commission and Safe Transactions",
                callback_data="reason_0"
            )
        ],
        [
            InlineKeyboardButton(
                "💰 高額佣金和安全交易",
                callback_data="reason_1"
            )
        ]
    ]

    await query.message.reply_text(
        "❓ Why should you work for our company?\n"
        "為什麼要加入我們公司？",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    )
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 TGPAY Tracker Bot\n\n"
        "আমি আপনার Telegram channel-এর activity tracking করছি.\n\n"
        "/invite - Tracking invite link তৈরি করুন\n"
        "/stats - Statistics দেখুন"
    )


async def create_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user

        link = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            name=f"user_{user.id}",
            creates_join_request=False,
        )

        invite_stats[link.invite_link] = {
            "owner_id": user.id,
            "owner_name": user.full_name,
            "joins": 0,
        }

        await update.message.reply_text(
            "✅ আপনার tracking invite link তৈরি হয়েছে:\n\n"
            f"{link.invite_link}\n\n"
            "এই link দিয়ে কেউ channel-এ join করলে সেটি track হবে।"
        )

    except Exception:
        logger.exception("Invite creation failed")

        await update.message.reply_text(
            "❌ Invite link তৈরি করা যায়নি।\n\n"
            "Bot-টি channel-এর Admin কিনা এবং "
            "'Invite Users via Link' permission ON আছে কিনা নিশ্চিত করুন।"
        )


async def member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.chat_member

    if not cm:
        return

    try:
        target_chat = await context.bot.get_chat(CHANNEL_ID)

        if cm.chat.id != target_chat.id:
            return

    except Exception:
        logger.exception("Could not verify channel")
        return

    old_status = cm.old_chat_member.status
    new_status = cm.new_chat_member.status
    user = cm.new_chat_member.user

    if old_status in ("left", "kicked") and new_status in (
        "member",
        "administrator",
    ):
        stats["joins"] += 1

        invite = cm.invite_link

        if invite:
            link = invite.invite_link

            if link in invite_stats:
                invite_stats[link]["joins"] += 1

            logger.info(
                "JOIN: %s via %s",
                user.full_name,
                link,
            )
        else:
            logger.info(
                "JOIN: %s via direct/unknown link",
                user.full_name,
            )

    elif new_status in ("left", "kicked"):
        stats["leaves"] += 1

        logger.info(
            "LEAVE: %s",
            user.full_name,
        )


async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post:
        stats["posts"] += 1

        logger.info(
            "New channel post: %s",
            update.channel_post.message_id,
        )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 TGPAY Tracker Statistics\n\n"
        f"📝 Channel posts detected: {stats['posts']}\n"
        f"👤 New joins detected: {stats['joins']}\n"
        f"🚪 Leaves detected: {stats['leaves']}\n"
        f"🔗 Tracking links: {len(invite_stats)}"
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(
        "Update caused error: %s",
        context.error,
        exc_info=context.error,
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("wallet", wallet_question))
    app.add_handler(CommandHandler("invite", create_invite))
    app.add_handler(CommandHandler("stats", show_stats))
    
    app.add_handler(CallbackQueryHandler(wallet_answer, pattern="^wallet_"))

   app.add_handler(
        ChatMemberHandler(
            member_update,
            ChatMemberHandler.CHAT_MEMBER,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.UpdateType.CHANNEL_POST,
            channel_post,
        )
    )

    app.add_error_handler(error_handler)

    app.run_polling(
        allowed_updates=[
            "message",
            "channel_post",
            "chat_member",
        ]
    )


if __name__ == "__main__":
    main()
