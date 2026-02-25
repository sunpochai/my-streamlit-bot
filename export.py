import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime

# 1. Setup Firebase (ชี้ไปที่ไฟล์ Key ของคุณ)
cred = credentials.Certificate("credential/trade-journal-c151f-firebase-adminsdk-fbsvc-1d2d72d603.json") # <-- แก้ Path ไฟล์นี้
firebase_admin.initialize_app(cred)
db = firestore.client()

# ฟังก์ชันแปลง Type ที่ JSON ปกติไม่รองรับ (เช่น Timestamp ของ Firestore)
def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat() # แปลงวันที่เป็น String ISO 8601
    raise TypeError(f"Type {type(obj)} not serializable")

def export_collection_to_json(collection_name, output_filename):
    print(f"กำลังดึงข้อมูลจาก Collection: {collection_name}...")
    
    # ดึงข้อมูลทั้งหมดใน Collection
    docs = db.collection(collection_name).stream()
    
    all_data = []
    for doc in docs:
        doc_dict = doc.to_dict()
        # เพิ่ม ID ของ Document เข้าไปใน Data ด้วย (เผื่อต้องใช้)
        doc_dict['_id'] = doc.id 
        all_data.append(doc_dict)
        
    # เขียนลงไฟล์ JSON
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4, default=json_serial)
        
    print(f"✅ Export เสร็จสิ้น! ได้ข้อมูล {len(all_data)} รายการ")
    print(f"ไฟล์ถูกบันทึกที่: {output_filename}")

# --- เรียกใช้งาน ---
# เปลี่ยนชื่อ Collection ที่ต้องการ Export ตรงนี้ (เช่น 'signals', 'users')
export_collection_to_json('Signal-Trading-Journal', 'Signal-Trading-Journal.json')