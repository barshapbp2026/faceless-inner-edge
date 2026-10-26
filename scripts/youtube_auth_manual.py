import os, pickle, re, sys
from google_auth_oauthlib.flow import Flow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
REDIRECT_URI = "http://localhost:8080/"

def main():
    if not os.path.exists("client_secret.json"):
        print("ERROR: client_secret.json not found in current directory.")
        sys.exit(1)

    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    print()
    print("=" * 70)
    print("STEP 1: Copy this URL into your Windows browser:")
    print("=" * 70)
    print(auth_url)
    print()
    print("=" * 70)
    print("STEP 2: Sign in and click Allow.")
    print("STEP 3: Browser will show 'This site can't be reached'.")
    print("        That's expected — do NOT close the tab.")
    print("STEP 4: Copy the FULL URL from the browser address bar")
    print("        (it contains code=...).")
    print("STEP 5: Paste it below and press Enter.")
    print("=" * 70)
    print()

    pasted = input("Paste full redirect URL (or just the code): ").strip()

    if "code=" in pasted:
        m = re.search(r"code=([^&]+)", pasted)
        code = m.group(1) if m else None
    else:
        code = pasted

    if not code:
        print("ERROR: no authorization code found.")
        sys.exit(1)

    flow.fetch_token(code=code)

    with open("token.pickle", "wb") as f:
        pickle.dump(flow.credentials, f)

    print()
    print("SUCCESS! New token saved to token.pickle")
    print("You can now run: python3 scripts/upload_youtube.py")

if __name__ == "__main__":
    main()
