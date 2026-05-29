import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import config
from database.db import init_db
from handlers import user, admin, payment
from aiohttp import web
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import User, Subscription
from keyboards.inline import help_os_keyboard
from services.marzban import MarzbanAPI
import time

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
marzban = MarzbanAPI()


async def process_successful_payment(
    user_id: int, action: str, sub_id: int, days: int, users: int
):
    async with AsyncSessionLocal() as session:
        if action == "buy":
            result = await session.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            subs = result.scalars().all()
            count = len(subs) + 1

            marzban_username = f"user_{user_id}_{count}_{int(time.time())}"
            try:
                await marzban.create_user(marzban_username, days)
                new_sub = Subscription(
                    user_id=user_id,
                    marzban_username=marzban_username,
                    name=f"Подписка №{count}",
                )
                session.add(new_sub)
                await session.commit()
                await bot.send_message(
                    user_id,
                    f"✅ <b>Оплата успешно завершена!</b> Добавлено {days} дней к вашему новому подключению.\n\n"
                    f"👉 Перейдите в раздел <b>🔑 Мои активные ключи</b>, чтобы скопировать ваш ключ доступа.\n"
                    f"👉 Чтобы настроить устройство прямо сейчас, выберите вашу операционную систему ниже:",
                    reply_markup=help_os_keyboard(),
                    parse_mode="HTML",
                )
            except Exception as e:
                logging.error(f"Error creating marzban sub: {e}")

        elif action == "extend":
            result = await session.execute(
                select(Subscription).where(
                    Subscription.id == sub_id, Subscription.user_id == user_id
                )
            )
            sub = result.scalar_one_or_none()
            if sub:
                try:
                    await marzban.add_days(sub.marzban_username, days)
                    await bot.send_message(
                        user_id,
                        f"✅ <b>Продление успешно завершено!</b> Добавлено {days} дней к вашей подписке.\n\n"
                        f"👉 Перейдите в раздел <b>🔑 Мои активные ключи</b>, чтобы скопировать ваш ключ доступа.",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logging.error(f"Error extending marzban sub: {e}")


async def platega_webhook(request):
    try:
        data = await request.json()
        logging.info(f"PLATEGA WEBHOOK RECEIVED: {data}")
        status = data.get("status")

        # Возможно, payload называется иначе:
        order_id = (
            data.get("payload") or data.get("orderId") or data.get("custom") or ""
        )

        parts = order_id.split("_")
        if len(parts) >= 7 and parts[0] == "order":
            user_id = int(parts[1])
            action = parts[2]
            sub_id = int(parts[3])
            days = int(parts[4])
            users = int(parts[5])

            if status in ["CONFIRMED", "success", "PAID", "paid", "SUCCESS"]:
                await process_successful_payment(user_id, action, sub_id, days, users)
                logging.info(f"Platega payment processed for {order_id}")
        return web.json_response({"status": "ok"})
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return web.json_response({"status": "ok"}, status=200)


async def cryptobot_webhook(request):
    try:
        # CryptoBot sends HMAC-SHA256 signature in 'Crypto-Pay-Api-Signature' header
        # For simplicity, we just process the status
        data = await request.json()
        payload = data.get("payload")
        status = data.get("status")

        if status == "paid" and payload:
            parts = payload.split("_")
            if len(parts) >= 7 and parts[0] == "order":
                user_id = int(parts[1])
                action = parts[2]
                sub_id = int(parts[3])
                days = int(parts[4])
                users = int(parts[5])
                await process_successful_payment(user_id, action, sub_id, days, users)
        return web.json_response({"status": "ok"})
    except Exception as e:
        logging.error(f"CryptoBot Webhook error: {e}")
        return web.json_response({"status": "error"}, status=400)


async def shortlink_redirect(request):
    try:
        short_id = request.match_info.get('short_id', '')
        if not short_id:
            return web.Response(text="Not found", status=404)
        
        # TODO: Implement shortlink resolution
        # Map short_id to subscription URL from Marzban
        return web.Response(text="Shortlink service is not configured yet.", status=501)
    except Exception as e:
        logging.error(f"Shortlink error: {e}")
        return web.Response(text="Error", status=500)


async def check_expiring_subscriptions():
    """Фоновая задача: уведомления об истечении подписки."""
    notified_today = set()
    last_reset_date = None
    while True:
        try:
            # Сбрасываем уведомления раз в сутки (в полночь UTC)
            from datetime import date
            today = date.today()
            if last_reset_date != today:
                notified_today.clear()
                last_reset_date = today

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Subscription).join(User)
                )
                subs = result.scalars().all()

                for sub in subs:
                    try:
                        user_data = await marzban.get_user(sub.marzban_username)
                        if not user_data or 'expire' not in user_data:
                            continue

                        expire_ts = user_data['expire']
                        if not expire_ts:
                            continue

                        now = int(time.time())
                        days_left = (expire_ts - now) / 86400
                        notify_key = f"{sub.user_id}_{sub.id}_{int(days_left)}"

                        if notify_key in notified_today:
                            continue

                        msg = None
                        if 2.5 < days_left <= 3.5:
                            msg = (
                                f"⏰ <b>Напоминание</b>\n\n"
                                f"Ваша подписка <b>{sub.name}</b> истекает через <b>3 дня</b>.\n"
                                f"Продлите сейчас, чтобы не потерять доступ!"
                            )
                        elif 0.5 < days_left <= 1.5:
                            msg = (
                                f"🔔 <b>Срочно!</b>\n\n"
                                f"Подписка <b>{sub.name}</b> истекает <b>завтра</b>!\n"
                                f"Не забудьте продлить."
                            )
                        elif -0.5 < days_left <= 0.5:
                            msg = (
                                f"❌ <b>Подписка истекла</b>\n\n"
                                f"Подписка <b>{sub.name}</b> закончилась.\n"
                                f"Продлите, чтобы восстановить доступ к VPN."
                            )

                        if msg:
                            from keyboards.inline import key_info_keyboard
                            await bot.send_message(
                                sub.user_id, msg,
                                reply_markup=key_info_keyboard(sub.id),
                                parse_mode="HTML"
                            )
                            notified_today.add(notify_key)
                            logging.info(f"Sent expiry notification to {sub.user_id} for {sub.name} ({days_left:.1f} days left)")

                    except Exception as e:
                        logging.debug(f"Skip sub {sub.id}: {e}")
                        continue

        except Exception as e:
            logging.error(f"Expiry check error: {e}")

        # Проверяем каждые 6 часов
        await asyncio.sleep(6 * 3600)


async def main():
    await init_db()

    # Установка команд бота (подсказки в меню)
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="admin", description="Панель администратора"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logging.error(f"Failed to set bot commands: {e}")

    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(payment.router)

    # Start web server for Payment Webhooks (HTTP — nginx handles SSL)
    app = web.Application()
    app.router.add_post("/platega/webhook", platega_webhook)
    app.router.add_post("/cryptobot/webhook", cryptobot_webhook)
    app.router.add_get("/s/{short_id}", shortlink_redirect)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8443)
    await site.start()

    logging.info("Starting HTTP server for Webhooks on 0.0.0.0:8443")
    logging.info("Starting subscription expiry checker...")

    # Launch background task for expiry notifications
    asyncio.create_task(check_expiring_subscriptions())

    logging.info("Starting Telegram bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

