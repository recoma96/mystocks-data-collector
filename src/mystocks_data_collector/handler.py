from modules.storage import S3Database


def handler():
    db = S3Database()
    print(db.list_keys())

    print("Hello World")
