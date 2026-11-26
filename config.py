import os


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()


config = Config()
