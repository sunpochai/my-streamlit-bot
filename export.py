import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime

# 1. Setup Firebase
cred = credentials.Certificate("credential/trade-journal.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def export_collection_to_json(collection_name, output_filename):
    print(f"กำลังดึงข้อมูล 100 ล่าสุดจาก Collection: {collection_name}...")

    # 🔥 ดึง 100 ล่าสุด (ต้องมี field timestamp ใน Firestore)
    docs = (
        db.collection(collection_name)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(100)
        .stream()
    )

    all_data = []
    for doc in docs:
        doc_dict = doc.to_dict()
        doc_dict['_id'] = doc.id
        all_data.append(doc_dict)

    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4, default=json_serial)

    print(f"✅ Export เสร็จสิ้น! ได้ข้อมูล {len(all_data)} รายการ")
    print(f"ไฟล์ถูกบันทึกที่: {output_filename}")

# --- run ---
export_collection_to_json('Signal-Trading-Journal', 'Signal-Trading-Journal.json')