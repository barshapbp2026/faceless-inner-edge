import os, pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
VIDEO_FILE = "output/final_video_subbed.mp4"
TITLE = "The Mystery of Dark Matter #shorts"
DESCRIPTION = "The mystery of dark matter explained. #space #science #shorts"
TAGS = ["space", "science", "darkmatter", "shorts"]
CATEGORY_ID = "28"

def get_authenticated_service():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            # Use run_console() for a manual copy-paste flow that works reliably in WSL
            creds = flow.run_console()
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)

def upload_video(youtube):
    body = {
        "snippet": {
            "title": TITLE,
            "description": DESCRIPTION,
            "tags": TAGS,
            "categoryId": CATEGORY_ID,
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")
    print(f"Uploaded! Video ID: {response['id']}")
    print(f"URL: https://youtube.com/shorts/{response['id']}")

if __name__ == "__main__":
    print("Authenticating with YouTube...")
    youtube = get_authenticated_service()
    print("Uploading video...")
    upload_video(youtube)
