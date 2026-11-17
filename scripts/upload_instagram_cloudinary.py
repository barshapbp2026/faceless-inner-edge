import os, time, requests, json
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

IG_USER_ID = os.getenv("IG_BUSINESS_ACCOUNT_ID")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
VIDEO_FILE = "output/final_video_subbed.mp4"

if os.path.exists("output/topic.json"):
    with open("output/topic.json", "r") as f: 
        topic_data = json.load(f)
    TITLE = topic_data.get("video_title", "Space Mystery")
    DESCRIPTION = topic_data.get("description", "")
    TAGS = " ".join(topic_data.get("tags", ["#space", "#science", "#reels"]))
    CAPTION = f"{TITLE}\n\n{DESCRIPTION}\n\n{TAGS}"
else:
    CAPTION = "Space Mystery\n\n#space #science #reels"

def upload_to_cloudinary(filepath):
    print("Uploading video to Cloudinary...")
    try:
        response = cloudinary.uploader.upload(filepath, resource_type="video", folder="instagram_reels")
        print("Cloudinary URL: " + response['secure_url'])
        return response['secure_url']
    except Exception as e:
        print("ERROR uploading: " + str(e))
        return None

def create_container(video_url):
    print("Creating Instagram media container...")
    r = requests.post(
        "https://graph.instagram.com/v26.0/" + IG_USER_ID + "/media",
        params={"media_type": "REELS", "video_url": video_url, "caption": CAPTION, "access_token": IG_ACCESS_TOKEN},
    )
    data = r.json()
    if "id" not in data:
        print("ERROR creating container:", data)
        return None
    return data["id"]

def wait_for_ready(container_id):
    print("Waiting for Instagram to process video...")
    for i in range(30):
        time.sleep(10)
        r = requests.get(
            "https://graph.instagram.com/v26.0/" + container_id,
            params={"fields": "status_code,status", "access_token": IG_ACCESS_TOKEN},
        )
        status = r.json().get("status_code")
        print("  [" + str(i+1) + "/30] Status: " + str(status))
        if status == "FINISHED": return True
        if status == "ERROR": return False
    return False

def publish_reel(container_id):
    print("Publishing Reel to Instagram...")
    r = requests.post(
        "https://graph.instagram.com/v26.0/" + IG_USER_ID + "/media_publish",
        params={"creation_id": container_id, "access_token": IG_ACCESS_TOKEN},
    )
    data = r.json()
    if "id" in data:
        print("\n✅ Published! Post ID: " + data["id"])
    else:
        print("ERROR publishing:", data)

if __name__ == "__main__":
    video_url = upload_to_cloudinary(VIDEO_FILE)
    if video_url:
        container_id = create_container(video_url)
        if container_id and wait_for_ready(container_id):
            publish_reel(container_id)
