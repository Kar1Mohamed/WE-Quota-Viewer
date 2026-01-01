import sys
import os
import socket
import requests
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timezone
from dotenv import load_dotenv

# ================= LOAD ENV =================
load_dotenv()

LANDLINE = os.getenv("WE_LANDLINE")
PASSWORD = os.getenv("WE_PASSWORD")

if not LANDLINE or not PASSWORD:
    messagebox.showerror("WE Tool", "Missing environment variables")
    sys.exit(1)

# ================= UI =================
app = tk.Tk()
app.withdraw()
app.title("WE Internet Quota Tool")

def die(msg):
    messagebox.showerror("WE Internet Quota Tool", msg)
    sys.exit(1)

# ================= NETWORK TEST =================
def network_alive():
    try:
        sock = socket.create_connection(("1.1.1.1", 53), timeout=3)
        sock.close()
        return True
    except Exception:
        return False

if not network_alive():
    die("Network unreachable")

# ================= CORE =================
class WEClient:
    BASE = "https://api-my.te.eg"  

    def __init__(self, landline, password):
        self.landline = landline
        self.password = password
        self.acct = "FBB" + landline[1:]
        self.session = requests.Session()
        self.token = None
        self.sub_id = None
        self.customer = None

    def _hdr(self, token=None):
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "WE-Desktop-Tool/1.0",
            "channelId": "702",
            "languageCode": "en-US",
            "isSelfcare": "true",
        }
        if token:
            h["csrftoken"] = token
        return h

    def bootstrap(self):
        url = f"{self.BASE}/echannel/service/besapp/base/rest/busiservice/v1/common/querySysParams"
        self.session.post(url, headers=self._hdr(), json={}).raise_for_status()

    def authenticate(self):
        url = f"{self.BASE}/echannel/service/besapp/base/rest/busiservice/v1/auth/userAuthenticate"
        payload = {
            "acctId": self.acct,
            "password": self.password,
            "appLocale": "en-US"
        }
        r = self.session.post(url, headers=self._hdr(), json=payload)
        data = r.json()

        if data["header"]["retCode"] != "0":
            die("Invalid credentials")

        body = data["body"]
        self.token = body["token"]
        self.sub_id = body["subscriber"]["subscriberId"]
        self.customer = body["customer"]["custName"]

    def current_offer(self):
        url = f"{self.BASE}/echannel/service/besapp/base/rest/busiservice/cz/v1/auth/getSubscribedOfferings"
        payload = {"msisdn": self.acct, "numberServiceType": "FBB"}
        r = self.session.post(url, headers=self._hdr(self.token), json=payload)
        return r.json()["body"]["offeringList"][0]["mainOfferingId"]

    def quota_info(self, offer_id):
        url = f"{self.BASE}/echannel/service/besapp/base/rest/busiservice/cz/cbs/bb/queryFreeUnit"
        payload = {"subscriberId": self.sub_id, "mainOfferId": offer_id}
        r = self.session.post(url, headers=self._hdr(self.token), json=payload)
        return r.json()["body"][0]

# ================= TIME =================
def human_time(ms):
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone()
    return dt.strftime("%d/%m/%Y %I:%M %p")

# ================= RUN =================
def run():
    client = WEClient(LANDLINE, PASSWORD)
    client.bootstrap()
    client.authenticate()

    offer_id = client.current_offer()
    q = client.quota_info(offer_id)

    used = q["used"]
    total = q["total"]
    remain = q["remain"]
    percent = (used / total) * 100

    msg = (
        f"Customer Name:\n{client.customer}\n"
        f"{'-'*30}\n"
        f"Package:\n{q['offerName']}\n\n"
        f"Usage:\n"
        f"Used: {used} GB\n"
        f"Remaining: {remain} GB\n"
        f"Total: {total} GB\n"
        f"Usage Percent: {percent:.1f}%\n\n"
        f"Renew Date: {human_time(q['effectiveTime'])}\n"
        f"Expiry Date: {human_time(q['expireTime'])}"
    )

    messagebox.showinfo("WE Internet Quota Tool", msg)

run()