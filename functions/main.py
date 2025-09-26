# functions/main.py

from firebase_admin import initialize_app, firestore, auth
from firebase_functions import https_fn, options, event_fn
import google.generativeai as genai
import datetime
import json
import os

initialize_app()
db = firestore.client()

GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
def get_inventory_http(request: https_fn.Request) -> https_fn.Response:
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise https_fn.HttpsError(code=https_fn.FunctionsErrorCode.UNAUTHENTICATED, message='Unauthorized')
    
    id_token = auth_header.split('Bearer ')[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        user_id = decoded_token['uid']
        
        inventory_ref = db.collection('inventories').document(user_id)
        inventory_doc = inventory_ref.get()
        
        inventory_data = []
        if inventory_doc.exists:
            inventory_data = inventory_doc.to_dict().get('cards', [])
        
        return https_fn.Response(json.dumps(inventory_data), status=200)
    except Exception as e:
        print(f"Error: {e}")
        raise https_fn.HttpsError(code=https_fn.FunctionsErrorCode.INTERNAL, message='Server error')

@event_fn.auth.on_user_created()
def create_user_profile(event: event_fn.Event[event_fn.auth.UserRecord]) -> None:
    try:
        user_id = event.data.uid
        email = event.data.email
        display_name = event.data.display_name or "New User"

        print(f"New user signed up! Creating profile for UID: {user_id}")

        db.collection('users').document(user_id).set({
            'displayName': display_name,
            'email': email,
            'createdAt': datetime.datetime.now(datetime.timezone.utc)
        })
        db.collection('inventories').document(user_id).set({ 'userId': user_id, 'cards': [] })
        
        print(f"Successfully created profile and inventory for {user_id}")
    except Exception as e:
        print(f"Error creating user profile: {e}")
