import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np

def makeCarDF(websiteURL):
    x = requests.get(websiteURL)

    soup = BeautifulSoup(x.text, 'lxml')
    gv_vehicles = soup.find(id='gvVehicles')
    rows = gv_vehicles.findAll('tr')

    # Holder Arrays
    car_details_date = []
    car_details_make = []
    car_details_klm = []
    car_details_transmission = []

    for row in rows:
        cells = row.find_all('td')
        
        if len(cells) > 2:

            # Extract image URL
            img_tag = cells[0].find('img')
            image_url = img_tag['src'] if img_tag else ''
            
            # Skip rows with the blank image
            if image_url == 'images/blank.jpg':
                continue

            # Extract vehicle name
            strong_tag = cells[2].find('strong')
            vehicle_name = strong_tag.string.strip()
            date = strong_tag.string[:4]

            car_details_date.append(date)
            
            # Extract vehicle details 
            vehicle_details_parts = [part.strip() for part in cells[2].strings if part.strip()]
            vehicle_details = ' '.join(vehicle_details_parts)
            vehicle_details = vehicle_details[-1 + len(vehicle_name) + 1:]

            # Split the string by double spaces to separate model and details
            parts = vehicle_details.split("  ")

            # The first part should be the model details
            model_details = parts[0]
            a = model_details.split(" ", 2)

            if re.search(r'([1-5][Dd])', a[2]):
                split_line = re.split(r'([1-5][Dd])', a[2])
                car_details_make.append(split_line[0])
            else:
                car_details_make.append(a[2])
            
            # Find the transmission 

            if re.search(r' AUTO ', vehicle_details) or re.search(r' AUTOMATIC ', vehicle_details) or re.search(r' AUTOMATED ', vehicle_details):
                car_details_transmission.append("Automatic")
            elif re.search(r' MANUAL ', vehicle_details):
                car_details_transmission.append("Manual")
            elif re.search(r' CONTINUOUS VARIABLE ', vehicle_details):
                car_details_transmission.append("CVT")
            elif re.search(r' SEQUENTIAL ', vehicle_details):
                car_details_transmission.append("Sequential")
            elif re.search(r' MULTITRONIC ', vehicle_details):
                car_details_transmission.append("Multitronic")
            elif re.search(r' ELECTRONIC ', vehicle_details):
                car_details_transmission.append("Electronic")
            else:
                print("Could not find transmission in: ", vehicle_details)
                car_details_transmission.append("Unknown")

            test = re.split(r'(\d+)\s*Klm',vehicle_details)
            car_details_klm.append(test[1] + " KM")

    data = {
        'Make & Model': car_details_make,
        'Production': car_details_date,
        'Transmission': car_details_transmission,
        'KM': car_details_klm,
    }
    df = pd.DataFrame(data)
    df['index_col'] = df.index

    # df.to_csv("car_data.csv", index=False)
    
    # Split the table
    chunk_size = 50
    num_chunks = np.ceil(len(df) / chunk_size).astype(int)
    chunks = [df.iloc[i*chunk_size:(i+1)*chunk_size] for i in range(num_chunks)]

    return chunks
#df.to_json(orient='records')
