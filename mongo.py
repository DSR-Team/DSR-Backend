from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime
load_dotenv()
CONNECTION_STRING = os.environ.get("CONNECTION_STRING")



def get_database(name, srv=CONNECTION_STRING):
    # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
    client = MongoClient(srv)
    # Create the database for our example (we will use the same database throughout the tutorial
    return client[name]

DB_showroom = get_database("showroom", CONNECTION_STRING)
Col_login = DB_showroom["login"]
Col_user = DB_showroom["user"]
Col_room = DB_showroom["room"]
