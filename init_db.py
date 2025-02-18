import aiosqlite
import asyncio

async def init_db():
    async with aiosqlite.connect('database/bot_database.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                warnings INTEGER DEFAULT 0,
                banned_until TIMESTAMP
            )
        ''')
        await db.commit()
        print("База данных успешно инициализирована.")

if __name__ == '__main__':
    asyncio.run(init_db())
