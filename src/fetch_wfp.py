import os
import requests

# 1. Dynamically fetch the latest download URL from the HDX API
print("Querying HDX API for the latest WFP dataset URL...")
dataset_api_url = (
    "https://data.humdata.org/api/3/action/package_show?id=wfp-global-food-prices"
)

metadata_response = requests.get(dataset_api_url)
metadata_response.raise_for_status()
resources = metadata_response.json().get("result", {}).get("resources", [])

wfp_download_url = None
for res in resources:
    # Look for the specific main CSV file
    if (
        res.get("format", "").upper() == "CSV"
        and "wfpvam_foodprices" in res.get("name", "").lower()
    ):
        wfp_download_url = res.get("url")
        break

if not wfp_download_url:
    raise ValueError("Could not locate the WFP CSV download URL from the HDX API.")

print(f"Live URL found: {wfp_download_url}")

# 2. Download the heavy CSV file locally to the GitHub runner
local_file = "wfpvam_foodprices_temp.csv"
print("Downloading WFP data...")

response = requests.get(wfp_download_url, stream=True)
response.raise_for_status()

with open(local_file, "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            f.write(chunk)

# 3. Upload to Databricks Volume
dbx_host = os.environ.get("DATABRICKS_HOST", "").replace("https://", "").strip("/")
dbx_token = os.environ.get("DATABRICKS_TOKEN")
dbx_path = "/Volumes/workspace/default/spi_data/samples/wfpvam_foodprices.csv"

if not dbx_host or not dbx_token:
    raise ValueError("Databricks credentials not found in environment variables.")

print(f"Uploading directly to Databricks Volume: {dbx_path}")
upload_url = f"https://{dbx_host}/api/2.0/fs/files{dbx_path}"
headers = {"Authorization": f"Bearer {dbx_token}"}

with open(local_file, "rb") as f:
    # 'overwrite=true' ensures we cleanly replace last week's file
    upload_url_with_params = f"{upload_url}?overwrite=true"
    upload_resp = requests.put(upload_url_with_params, headers=headers, data=f)

upload_resp.raise_for_status()
print("Upload complete! File is now ready for Databricks processing.")

# 4. Clean up the heavy temp file
os.remove(local_file)
