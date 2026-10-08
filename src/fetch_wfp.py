import os
import requests

# 1. Download from HDX API
wfp_api_url = "https://data.humdata.org/dataset/999b66ee-5c62-4afc-bfab-d72b22fcebc2/resource/71542fba-3837-4d7a-b9c1-4b13a7c36a32/download/wfpvam_foodprices.csv"
local_file = "wfpvam_foodprices_temp.csv"

print("Downloading WFP data from HDX API...")
response = requests.get(wfp_api_url, stream=True)
response.raise_for_status()

with open(local_file, "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

# 2. Upload to Databricks Volume
dbx_host = os.environ.get("DATABRICKS_HOST", "").replace("https://", "").strip("/")
dbx_token = os.environ.get("DATABRICKS_TOKEN")
dbx_path = "/Volumes/workspace/default/spi_data/samples/wfpvam_foodprices.csv"

if not dbx_host or not dbx_token:
    raise ValueError("Databricks credentials not found in environment variables.")

print(f"Uploading directly to Databricks Volume: {dbx_path}")
upload_url = f"https://{dbx_host}/api/2.0/fs/files{dbx_path}"
headers = {"Authorization": f"Bearer {dbx_token}"}

with open(local_file, "rb") as f:
    upload_resp = requests.put(upload_url, headers=headers, data=f)

upload_resp.raise_for_status()
print("Upload complete! File is now ready for Databricks processing.")

# 3. Clean up the heavy temp file so it doesn't get pushed to Git
os.remove(local_file)
