import os
import requests

# 1. Dynamically fetch the live download URL from the HDX API
print("Querying HDX API for the live WFP dataset URL...")
dataset_api_url = (
    "https://data.humdata.org/api/3/action/package_show?id=wfp-global-food-prices"
)

metadata_response = requests.get(dataset_api_url)
metadata_response.raise_for_status()
resources = metadata_response.json().get("result", {}).get("resources", [])

wfp_download_url = None
for res in resources:
    if (
        res.get("format", "").upper() == "CSV"
        and "wfpvam_foodprices" in res.get("name", "").lower()
    ):
        wfp_download_url = res.get("url")
        break

if not wfp_download_url:
    raise ValueError("Could not locate the WFP CSV download URL from the HDX API.")

print(f"Live URL found. Establishing direct stream to Databricks...")

# 2. Prepare Databricks REST API connection
dbx_host = os.environ.get("DATABRICKS_HOST", "").replace("https://", "").strip("/")
dbx_token = os.environ.get("DATABRICKS_TOKEN")
dbx_path = "/Volumes/workspace/default/spi_data/samples/wfpvam_foodprices.csv"

if not dbx_host or not dbx_token:
    raise ValueError("Databricks credentials not found in environment variables.")

upload_url = f"https://{dbx_host}/api/2.0/fs/files{dbx_path}?overwrite=true"
headers = {"Authorization": f"Bearer {dbx_token}"}

# 3. Stream data DIRECTLY from the HDX API into the Databricks API (No files saved!)
with requests.get(wfp_download_url, stream=True) as source_response:
    source_response.raise_for_status()

    # We pass the incoming API stream generator directly to the outgoing Databricks PUT request
    print("Piping data from HDX API directly into Databricks Volume...")
    upload_resp = requests.put(
        upload_url, headers=headers, data=source_response.iter_content(chunk_size=8192)
    )

upload_resp.raise_for_status()
print("Direct API stream complete! Data is instantly ready in Databricks.")
