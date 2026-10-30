import os, pickle, json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]
VIDEO_FILE = "output/final_video_subbed.mp4"
CATEGORY_ID = "28"

if os.path.exists("output/topic.json"):
    with open("output/topic.json", "r") as f: data = json.load(f)
    TITLE = f"{data.get('video_title', 'Space Mystery')} | Full Documentary"
    DESCRIPTION = data.get("description", "") + "\n\n" + " ".join(data.get("tags", []))
    TAGS = data.get("tags", [])
else:
    TITLE = "Space Mystery"
    DESCRIPTION = ""
    TAGS = []

def get_authenticated_service():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f: creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as f: pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)

def upload_video(youtube):
    # CHANGED TO PUBLIC HERE
    body = {"snippet": {"title": TITLE, "description": DESCRIPTION, "tags": TAGS, "categoryId": CATEGORY_ID}, "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    media = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status: print(f"Uploaded {int(status.progress() * 100)}%")
    video_id = response['id']
    print(f"Uploaded! Video ID: {video_id}")

    if os.path.exists("output/thumbnail.jpg"):
        print("Uploading custom AI thumbnail...")
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload("output/thumbnail.jpg")).execute()
            print("Thumbnail set successfully!")
        except Exception as e: print(f"Failed to set thumbnail: {e}")

if __name__ == "__main__":
    youtube = get_authenticated_service()
    upload_video(youtube)
