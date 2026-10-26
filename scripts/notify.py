import subprocess
import os
from datetime import datetime

VIDEO_PATH = "output/final_video_subbed.mp4"
LOG_FILE = "logs/notifications.log"

abs_path = os.path.abspath(VIDEO_PATH)

# Log the notification
os.makedirs("logs", exist_ok=True)
with open(LOG_FILE, "a") as f:
    f.write(f"{datetime.now()} - Video ready for X: {abs_path}\n")

# Windows toast notification
ps_script = '''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>New Video Ready for X</text>
            <text>Upload final_video_subbed.mp4 manually to X</text>
        </binding>
    </visual>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Faceless Pipeline").Show($toast)
'''

try:
    subprocess.run(["powershell.exe", "-Command", ps_script], timeout=10)
    print(f"Notification sent: {abs_path}")
except Exception as e:
    print(f"Notification failed: {e}")
    print(f"Video still ready at: {abs_path}")
