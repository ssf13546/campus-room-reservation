"""初始化数据库：建表 + 创建默认账号 + 插入演示房间。"""

from app import create_app, db
from app.models import User, Room

app = create_app()


def init():
    with app.app_context():
        db.create_all()

        # 默认账号
        if User.query.filter_by(username="admin").first() is None:
            admin = User(username="admin", name="管理员", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)

        if User.query.filter_by(username="student").first() is None:
            student = User(username="student", name="学生", role="student")
            student.set_password("student123")
            db.session.add(student)

        # 演示房间
        if Room.query.count() == 0:
            db.session.add_all([
                Room(name="A101", location="A栋 1楼", capacity=10,
                     equipment="投影仪、白板", status="available",
                     description="标准自习室，可容纳 10 人"),
                Room(name="A102", location="A栋 1楼", capacity=6,
                     equipment="白板", status="available",
                     description="小型讨论室"),
                Room(name="B201", location="B栋 2楼", capacity=20,
                     equipment="投影仪、音响", status="available",
                     description="中型会议室"),
                Room(name="B202", location="B栋 2楼", capacity=8,
                     equipment="无", status="maintenance",
                     description="小型会议室，当前维护中"),
            ])

        db.session.commit()
        print("数据库初始化完成：默认账号 admin/admin123、student/student123，演示房间已就绪。")


if __name__ == "__main__":
    init()
