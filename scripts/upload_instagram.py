import os, time, requests
from dotenv import load_dotenv

load_dotenv()

IG_USER_ID = os.getenv("IG_BUSINESS_ACCOUNT_ID")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
VIDEO_FILE = "output/final_video_subbed.mp4"
CAPTION = "The mystery of dark matter, explained in 60 seconds. #space #science #reels #darkmatter"

def upload_to_tmpfiles(filepath):
    print("Uploading video to tmpfiles.org (temporary public URL)...")
    with open(filepath, "rb") as f:
        r = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f})
    data = r.json()
    if data.get("status") != "success":
        print("ERROR uploading to tmpfiles:", data)
        return None
    # tmpfiles returns a URL like https://tmpfiles.org/12345/file.mp4
    # but direct downloads need /dl/ inserted
    public_url = data["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
    print(f"Public URL: {public_url}")
    return public_url

def create_container(video_url):
    print("Creating Instagram media container...")
    r = requests.post(
        f"https://graph.instagram.com/v18.0/{IG_USER_ID}/media",
        params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": CAPTION,
            "access_token": IG_ACCESS_TOKEN,
        },
    )
    data = r.json()
    if "id" not in data:
        print("ERROR creating container:", data)
        return None
    print(f"Container ID: {data['id']}")
    return data["id"]

def wait_for_ready(container_id):
    print("Waiting for Instagram to process video (this takes 30-90 seconds)...")
    for i in range(30):
        time.sleep(10)
        r = requests.get(
            f"https://graph.instagram.com/v18.0/{container_id}",
            params={"fields": "status_code,status", "access_token": IG_ACCESS_TOKEN},
        )
        data = r.json()
        status = data.get("status_code")
        print(f"  [{i+1}/30] Status: {status}")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            print("ERROR processing video:", data)
            return False
    print("TIMEOUT: Instagram took too long")
    return False

def publish_reel(container_id):
    print("Publishing Reel to Instagram...")
    r = requests.post(
        f"https://graph.instagram.com/v18.0/{IG_USER_ID}/media_publish",
        params={"creation_id": container_id, "access_token": IG_ACCESS_TOKEN},
    )
    data = r.json()
    if "id" not in data:
        print("ERROR publishing:", data)
        return
    print(f"\n✅ Published! Post ID: {data['id']}")
    print(f"   Check your Instagram profile: @inneredgemind2026")

if __name__ == "__main__":
    video_url = upload_to_tmpfiles(VIDEO_FILE)
    if not video_url:
        exit(1)
    container_id = create_container(video_url)
    if not container_id:
        exit(1)
    if wait_for_ready(container_id):
        publish_reel(container_id)
