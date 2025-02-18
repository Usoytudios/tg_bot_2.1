import asyncio
import aiosqlite
from config import db_path

async def list_users():
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT id, telegram_id, username, warnings, banned_until FROM users") as cursor:
            users = await cursor.fetchall()
            for user in users:
                print(f"{user[0]}. Telegram ID: {user[1]}, Username: {user[2]}, Warnings: {user[3]}, Banned Until: {user[4]}")

async def ban_user(user_id: int, permanent=False):
    async with aiosqlite.connect(db_path) as db:
        if permanent:
            await db.execute("UPDATE users SET banned_until = ? WHERE id = ?", (9999999999, user_id))
        else:
            import time
            await db.execute("UPDATE users SET banned_until = ? WHERE id = ?", (time.time() + 60, user_id))
        await db.commit()

async def unban_user(user_id: int):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE users SET banned_until = NULL, warnings = 0 WHERE id = ?", (user_id,))
        await db.commit()

async def delete_user(user_id: int):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()

async def admin_loop():
    print("Admin utility. Введите help для списка команд.")
    while True:
        cmd = input("admin> ").strip().lower()
        if cmd in ("help", "h"):
            print("Доступные команды: help, list, ban <id>, unban <id>, delete <id>, permaban <id>, exit")
        elif cmd.startswith("list"):
            await list_users()
        elif cmd.startswith("ban "):
            try:
                user_id = int(cmd.split()[1])
                await ban_user(user_id)
                print(f"Пользователь {user_id} забанен.")
            except Exception as e:
                print("Ошибка:", e)
        elif cmd.startswith("permaban "):
            try:
                user_id = int(cmd.split()[1])
                await ban_user(user_id, permanent=True)
                print(f"Пользователь {user_id} получил перманентный бан.")
            except Exception as e:
                print("Ошибка:", e)
        elif cmd.startswith("unban "):
            try:
                user_id = int(cmd.split()[1])
                await unban_user(user_id)
                print(f"Пользователь {user_id} разбанен.")
            except Exception as e:
                print("Ошибка:", e)
        elif cmd.startswith("delete "):
            try:
                user_id = int(cmd.split()[1])
                await delete_user(user_id)
                print(f"Пользователь {user_id} удален из базы.")
            except Exception as e:
                print("Ошибка:", e)
        elif cmd in ("exit", "quit"):
            print("Выход из админ утилиты.")
            break
        else:
            print("Неизвестная команда. Введите help для списка команд.")

if __name__ == '__main__':
    asyncio.run(admin_loop())
