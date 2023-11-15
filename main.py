import json
import requests
from datetime import datetime, timezone
import os
from PIL import Image
from pprint import pprint
import piexif
import subprocess

def get_file_name(download, file_time):
    file_extension = "jpg" if download["Media Type"].lower() in ["image", "photo"] else "mp4"
    return f"{file_time.strftime('%Y-%m-%d_%H-%M-%S')}.{file_extension}"

def get_download_link(url, body, file_name, file_time):
    parsed_url = requests.utils.urlparse(url)
    options = {
        "hostname": parsed_url.hostname,
        "path": parsed_url.path,
        "method": "POST",
        "headers": {
            "Content-Type": "application/x-www-form-urlencoded",
        },
    }

    def get_link(max_retries):
        try:
            response = requests.post(url, data=body, headers=options["headers"])
            if response.status_code == 200:
                return response.text, file_name, file_time
            elif max_retries > 0:
                return get_link(max_retries - 1)
            else:
                raise Exception("status error")
        except:
            if max_retries > 0:
                return get_link(max_retries - 1)
            else:
                raise Exception("request error")

    return get_link(3)

def download_memory(download_url, file_name, file_time):
    def download(max_retries):
        try:
            response = requests.get(download_url)
            if response.status_code == 200:
                with open(file_name, "wb") as file:
                    file.write(response.content)
                os.utime(file_name, (file_time.timestamp(), file_time.timestamp()))
                return True
            elif max_retries > 0:
                return download(max_retries - 1)
            else:
                raise Exception("status error")
        except:
            if max_retries > 0:
                return download(max_retries - 1)
            else:
                raise Exception("request error")

    return download(3)


def main(json):
    # Load data from JSON file
    with open(json) as f:
        data = json.load(f)

    output_dir = "Downloads"
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    for entry in data["Saved Media"]:
        date_string = entry["Date"]
        media_type = entry["Media Type"]
        location_string = entry["Location"]

        coordinates = location_string.split(": ")[1].split(", ")
        latitude = float(coordinates[0].strip())
        longitude = float(coordinates[1].strip())

        download_link = entry["Download Link"]
        body = download_link.split("?", 1)[1]
        file_time = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S %Z").replace(tzinfo=timezone.utc)

        file_name = get_file_name(entry, file_time)

        cdn_link, file_name, file_time = get_download_link(download_link, body, file_name, file_time)

        if download_memory(cdn_link, os.path.join(output_dir, file_name), file_time):
            print(f"Downloaded: {file_name}")
            print(f"Date: {date_string}")
            print(f"Location: Latitude {latitude}, Longitude {longitude}")

            # Update EXIF data
            exif_path = os.path.join(output_dir, file_name)
            cmd = [
                "exiftool",
                "-GPSLatitude={}".format(latitude),
                "-GPSLatitudeRef={}".format('N' if latitude >= 0 else 'S'),
                "-GPSLongitude={}".format(longitude),
                "-GPSLongitudeRef={}".format('E' if longitude >= 0 else 'W'),
                "-Model=Snapchat",
                "-Make=Snapchat",
                exif_path
            ]
            
            try:
                if latitude != 0 or longitude != 0:
                    subprocess.run(cmd, check=True)
                    print("Geolocation data added to", exif_path)
            except subprocess.CalledProcessError as e:
                print("Error:", e)
            
            
            # Update file modification time
            os.utime(exif_path, (file_time.timestamp(), file_time.timestamp()))

            print("EXIF updated")

            print()
        else:
            print(f"Download failed for: {file_name}")
            print()

    print("Processing finished.")

def get_gps_degrees(decimal_degrees):
    degrees = int(decimal_degrees)
    minutes = int((decimal_degrees - degrees) * 60)
    seconds = int(((decimal_degrees - degrees) * 60 - minutes) * 60 * 1000)
    return [(degrees, 1), (minutes, 1), (seconds, 1000)]

if __name__ == '__main__':
    main("memories_history.json")
