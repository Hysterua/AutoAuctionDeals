from scrape import makeCarDF
import google.generativeai as genai
import pandas as pd
import json
import os
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# --- Read the prompt from the text file ---
with open('gpt-prompt.txt', 'r') as file:
    gpt_prompt_template = file.read()

carAuctionURL = 'https://www.auto-auctions.com.au/search_results.aspx?sitekey=AAV&make=All%20Makes&model=All%20Models&keyword=&fromyear=From%20Any&toyear=To%20Any&body=All%20Body%20Types'
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-pro')

# Run scrape.py makeCarDF to get all necessary data.
carChunks = makeCarDF(carAuctionURL)

holding_json = {}

for i, chunk in enumerate(carChunks):
    while True:
        try:
            print(f"Chunk {i+1}:\n", chunk, "\n")
            print("Passing to Gemini API\n")
            
            temp_df = chunk.to_json(orient='records')

            gptPrompt = gpt_prompt_template + temp_df

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
