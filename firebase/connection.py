import firebase_admin
from firebase_admin import credentials, storage, db
import os
from dotenv import load_dotenv
load_dotenv()

cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_KEY'))
firebase_admin.initialize_app(cred, {
    'storageBucket': 'chuanai-c4de2.appspot.com',
    'databaseURL': 'https://chuanai-c4de2-default-rtdb.asia-southeast1.firebasedatabase.app'
})

bucket = storage.bucket()
db_ref = db.reference('/')