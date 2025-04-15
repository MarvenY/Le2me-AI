import pandas as pd
from googleapiclient.discovery import build
import firebase_admin
from firebase_admin import credentials, firestore
import sys
import time

# Initialize Firebase Admin with your service account credentials.
cred = credentials.Certificate(r"C:\Users\Administrator\Downloads\le2me-31b92-firebase-adminsdk-c9rvb-c7cb2b5f67.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Google Custom Search API credentials.
API_KEY = 'AIzaSyAccnLX3CwxDnjFRQpyKi0lZepQhGMlEWc'
CSE_ID = '421dd097948804bf7'

def google_search_image(query, api_key, cse_id):
    """
    Searches Google Images for the given query and returns the first image URL.
    Raises an Exception("QUOTA REACHED") if the Google API quota is exceeded.
    """
    try:
        service = build("customsearch", "v1", developerKey=api_key)
        res = service.cse().list(
            q=query,
            cx=cse_id,
            searchType='image',
            num=1  # Only fetch the first image result.
        ).execute()
        
        if 'items' in res:
            return res['items'][0]['link']
        else:
            return None
    except Exception as e:
        error_message = str(e).lower()
        if "quota" in error_message or "exceeded" in error_message:
            raise Exception("QUOTA REACHED")
        else:
            print(f"Error searching for '{query}': {e}")
            return None

# -----------------------------------------------
# Part 1: Re-fetch images for documents with "No image found" 
# (or that haven't been updated with a valid image)
# -----------------------------------------------
max_retries = 3
for attempt in range(max_retries):
    print(f"\nRe-fetch attempt {attempt+1} of {max_retries}")
    failed_docs = list(db.collection("default recipe").where("image_url", "==", "No image found").stream())
    if not failed_docs:
        print("All documents have valid image URLs.")
        break

    print(f"Found {len(failed_docs)} documents with 'No image found'.")
    for doc in failed_docs:
        doc_data = doc.to_dict()
        title = doc_data.get("title", "")
        doc_index = doc_data.get("index", "N/A")
        doc_id = doc.id
        try:
            new_image_url = google_search_image(title, API_KEY, CSE_ID)
        except Exception as e:
            if str(e) == "QUOTA REACHED":
                print("QUOTA REACHED during re-fetching. Exiting.")
                sys.exit(1)
        if new_image_url:
            db.collection("default recipe").document(doc_id).update({"image_url": new_image_url})
            print(f"Updated document {doc_id} (index {doc_index}) for recipe '{title}' with new image: {new_image_url}")
        else:
            # Update with marker so it is not searched again.
            db.collection("default recipe").document(doc_id).update({"image_url": "No available photo"})
            print(f"Could not retrieve image for '{title}' (index {doc_index}). Updated to 'No available photo'.")
        time.sleep(1)  # Pause briefly between requests.

    # Wait a moment before the next attempt
    time.sleep(2)

# Check final count of documents still missing valid images.
remaining = list(db.collection("default recipe").where("image_url", "==", "No image found").stream())
print(f"\nAfter re-fetch attempts, {len(remaining)} documents still have 'No image found'.")

# -----------------------------------------------
# Part 2: Process CSV file for new entries
# -----------------------------------------------
# Determine the last processed index from Firestore.
last_index = -1  # Default if no documents are found.
try:
    docs = db.collection("default recipe").order_by("index", direction=firestore.Query.DESCENDING).limit(1).stream()
    for doc in docs:
        doc_data = doc.to_dict()
        last_index = doc_data.get("index", -1)
        print(f"Last processed index found: {last_index}")
        break
except Exception as e:
    print(f"Error retrieving last index from Firestore: {e}")

csv_file = 'full_dataset.csv'
chunk_size = 1000  # Adjust based on your system's capacity.
quota_reached = False

# Loop through the CSV file in chunks.
for chunk in pd.read_csv(csv_file, chunksize=chunk_size):
    for _, row in chunk.iterrows():
        try:
            row_index = row['index']
            # Skip rows that have already been processed.
            if row_index <= last_index:
                continue
        except Exception as e:
            print(f"Error reading row index: {e}")
            continue
        
        title = row['title']
        directions = row['directions']
        recipe_link = row['link']
        source = row['source']
        ner = row['NER']
        
        try:
            image_url = google_search_image(title, API_KEY, CSE_ID)
        except Exception as e:
            if str(e) == "QUOTA REACHED":
                print("QUOTA REACHED during CSV processing. Exiting.")
                quota_reached = True
                break
        
        # If no image URL is found, set marker to avoid re-searching.
        if not image_url:
            image_url = "No available photo"
        
        data = {
            'index': row_index,
            'title': title,
            'directions': directions,
            'link': recipe_link,
            'source': source,
            'NER': ner,
            'image_url': image_url
        }
        
        db.collection("default recipe").add(data)
        print(f"Added recipe '{title}' (index {row_index}) with image: {data['image_url']}")
    
    if quota_reached:
        break

if quota_reached:
    print("Data upload stopped due to QUOTA REACHED")
else:
    print("Data upload complete!")
