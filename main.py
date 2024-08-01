from scrape import makeCarDF
import google.generativeai as genai
import pandas as pd
import json
import os
from dotenv import load_dotenv

load_dotenv()

carAuctionURL = 'https://www.auto-auctions.com.au/search_results.aspx?sitekey=AAV&make=All%20Makes&model=All%20Models&keyword=&fromyear=From%20Any&toyear=To%20Any&body=All%20Body%20Types'
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

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

            Return the result as a table in json format. Do not return anything other 
            than valid json. Do not preface with 'JSON' and don't make it a multiline string.
            Reference each with its index value in the format:

            Return this in the format:
            Index : {
                Make & Model
                Year
                Transmission
                # of KMS
                Retail Price Guide
                Lowest Price from the Price Guide
                KW
                Weight
                }

            the Lowest Price from the Price Guide should not have a $ sign.
            Price guide should have $ signs and be in the format "$X - $Y".
            the # of KMs should be an integer without 'KM'.

            LIST
            This is the list: """ +  temp_df

            print("Waiting...\n")

            response = model.generate_content(gptPrompt)

            print(response.text)

            temp_json = json.loads(response.text)

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

df['KW Per Ton'] = (df['KW'] / df['Weight'] * 1000).astype(int)
df['Lowest Price from the Price Guide'] = df['Lowest Price from the Price Guide'].astype(int)

# Filter the DF
df_filtered = df.loc[(df['KW Per Ton'] >= 110) & (df['# of KMS'] <= 150000) & (df['Lowest Price from the Price Guide'] <= 20000)]

print("Applying Filters and Saving the DF\n")

df_filtered.to_csv("car_data_GPT.csv", index=False)

print("Done!\n")
