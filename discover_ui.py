"""Run this script to discover Wellcee UI element resource-ids interactively.
Navigate the app to the screen you want to inspect, then press Enter."""
import uiautomator2 as u2
import os
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()
device_id = os.getenv("DEVICE_ID")
d = u2.connect(device_id) if device_id else u2.connect()

print("Connected to:", d.info["productName"])
print("\nNavigate Wellcee app to the screen you want to inspect, then press Enter.")

while True:
    input("\n[Enter] to dump UI hierarchy (Ctrl+C to quit): ")
    xml = d.dump_hierarchy()
    root = ET.fromstring(xml)
    for node in root.iter():
        rid = node.attrib.get("resource-id", "")
        text = node.attrib.get("text", "")
        desc = node.attrib.get("content-desc", "")
        cls = node.attrib.get("class", "")
        if rid or text or desc:
            print(f"  [{cls}] id={rid!r} text={text!r} desc={desc!r}")
