from mystocks_data_collector.modules.storage import S3Database


def handler(event, context):
    db = S3Database()
    print(db.list_keys())

    print("Hello World")
