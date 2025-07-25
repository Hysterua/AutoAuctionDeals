from scrape import makeCarDF
import google.generativeai as genai
import pandas as pd
import json
import os
from dotenv import load_dotenv
import numpy as np

load_dotenv()

carAuctionURL = 'https://www.auto-auctions.com.au/search_results.aspx?sitekey=AAV&make=All%20Makes&model=All%20Models&keyword=&fromyear=From%20Any&toyear=To%20Any&body=All%20Body%20Types'
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-pro')

carChunks = makeCarDF(carAuctionURL)

holding_json = {}

for i, chunk in enumerate(carChunks):
    while True:
        try:
            print(f"Chunk {i+1}:\n", chunk, "\n")
            print("Passing to Gemini API\n")
            
            temp_df = chunk.to_json(orient='records')

            gptPrompt = """
            JOB

            I'm about to pass in a list of cars from an auction site (in json format). You
            must then find a rough price guide for each from carsales.com.au (based off similar kilometres in the same car), find the
            kw for each (as an integer) and the cars weight in kg (as an integer).

            **Your response MUST be a single string containing valid JSON and absolutely nothing else.** Do not include any surrounding text, code blocks, or any other formatting. The JSON should be formatted like this example:

            {
              "0": {
                "Make & Model": "ALFA ROMEO GIULIETTA DISTINCTIVE",
                "Year": 2015,
                "Transmission": "Automatic",
                "# of KMS": 120371,
                "Retail Price Guide": "$15,000 - $20,000",
                "Lowest Price from the Price Guide": "15000",
                "KW": 110,
                "Weight": 1300
              },
              "1": {
                "Make & Model": "AUDI A3 S/B 1.8 TFSI QUATTRO AMBITION 8V ",
                "Year": 2013,
                "Transmission": "Automatic",
                "# of KMS": 197226,
                "Retail Price Guide": "$18,000 - $23,000",
                "Lowest Price from the Price Guide": "18000",
                "KW": 132,
                "Weight": 1395
              },
              // ... and so on for all cars in the list
              "49": {
                "Make & Model": "FORD RANGER WILDTRAK 2.0 (4x4) PX MKIII MY20.25 DOUBLE CAB P/UP",
                "Year": 2020,
                "Transmission": "Automatic",
                "# of KMS": 86845,
                "Retail Price Guide": "$50,000 - $60,000",
                "Lowest Price from the Price Guide": "50000",
                "KW": 157,
                "Weight": 2200
              }
            }

            **Crucial Instructions:**

            * **Your ENTIRE response MUST be a valid JSON string. Do not add any other characters or formatting.**
            * Do not enclose the JSON in a code block (like ```json ... ```) or any other type of formatting.
            * Reference each car with its original index value from the input list as the key in the top-level JSON object (e.g., "0", "1", "2", etc.).
            * The value for each index should be a JSON object with the following keys:
                * `"Make & Model"`: The full make and model of the car (string).
                * `"Year"`: The production year of the car (integer).
                * `"Transmission"`: The transmission type (string).
                * `"# of KMS"`: The number of kilometers as an **integer** (without the " KM" suffix).
                * `"Retail Price Guide"`: A string in the format **"$X - $Y"**.
                * `"Lowest Price from the Price Guide"`: The lower bound of the retail price guide as a **string representing an integer** (without the "$" sign).
                * `"KW"`: The power output in kilowatts as an **integer**.
                * `"Weight"`: The weight of the car in kilograms as an **integer**.

            LIST
            This is the list: """ +  temp_df

            print("Waiting...\n")

            response = model.generate_content(gptPrompt)
            response_text = response.text
            print(response.text)

            if response_text.startswith("```json") and response_text.endswith("```"):
                response_text = response_text[7:-3].strip()

            temp_json = json.loads(response_text)

            for key, entry in temp_json.items():
                lowest_price = entry.get('Lowest Price from the Price Guide')
                if lowest_price is None or lowest_price.lower() == "N/A":
                    raise ValueError(f"Error: 'Lowest Price from the Price Guide' is empty or N/a for entry with key {key}")

            holding_json.update(temp_json)

            print(f"\nFinished Chunk {i+1}\n")
            
            break  # Break out of the while loop if successful
        except Exception as e:
            print(f"Error processing Chunk {i+1}: {e}")
            print("Restarting the loop...\n")
            continue  # Restart the loop if there's an error

print("Finished the loop\n")

df = pd.DataFrame.from_dict(holding_json, orient='index')

# Replace inf with NaN
df.replace([np.inf, -np.inf], np.nan, inplace=True)

# Replace NaN with 1
df.fillna(1, inplace=True)

df['KW Per Ton'] = (df['KW'] / df['Weight'] * 1000).astype(int)
df['Lowest Price from the Price Guide'] = df['Lowest Price from the Price Guide'].astype(int)

# Filter the DF
df_filtered = df.loc[(df['KW Per Ton'] >= 110) & (df['# of KMS'] <= 200000) & (df['Lowest Price from the Price Guide'] <= 22000)]

print("Applying Filters and Saving the DF\n")

df_filtered.to_csv("car_data_GPT.csv", index=False)

print("Done!\n")
