import pandas as pd
import time
import os
import google.generativeai as genai
import logging

logging.basicConfig(level=logging.INFO)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel('gemini-2.0-flash-lite')

# Load the CSV file
df = pd.read_csv("/Users/or.hershko/Desktop/APT.-Scanner/tlv_data.csv", encoding='utf-8-sig')

# Drop the first row if it's acting as a header
# df = df.drop(0)

# Initialize an empty list to store summaries
summaries = []

# Iterate through each row in the DataFrame
for i, row in df.iterrows():
    neighborhood_name = row['English Neighborhood Name']

    logging.info(f"Processing neighborhood: {neighborhood_name}")

    # Construct the prompt for the language model
    prompt = f"""
    You are an expert real estate agent.
    I want you to give me a general overview (around 3 sentences) in English of the neighborhood {neighborhood_name} in Tel Aviv.
    Make sure to include the following details:
    - The general atmosphere of the neighborhood
    - The types of people who live there
    - The types of businesses in the area
    - The general vibe of the neighborhood
    The answer should be in a friendly and informative tone, and should be easy to understand.
    Do not include any personal opinions or subjective statements.
    Do not include in the answer any text that it not the general overview of the neighborhood.
    """

    try:
        # Generate content using the language model
        response = model.generate_content(prompt)
        summary = response.text
        logging.info(f"Response: {summary}")
        summaries.append(summary)
    except Exception as e:
        logging.error(f"Error generating summary for {neighborhood_name}: {e}")
        summaries.append(None)  # Append None if there's an error
    time.sleep(2)  # Polite delay to avoid hitting API limits

# Add the summaries to the DataFrame
df['Generated Overview'] = summaries

# Save the updated DataFrame to a new CSV file
df.to_csv("tlv_data_with_summaries.csv", encoding='utf-8-sig', index=False)

logging.info("✔ All done. Data saved to tlv_data_with_summaries.csv")
