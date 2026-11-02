import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(INSTANCE_DIR, "reservation.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 全局营业时间（所有房间统一）
    OPEN_TIME = "08:00"
    CLOSE_TIME = "22:00"
