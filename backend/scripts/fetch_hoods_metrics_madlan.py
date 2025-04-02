import os
import time
import json
import pandas as pd
from data.scrapers.madlan_scraper import MadlanScraper

def main():
    # Load Excel file and extract neighborhoods
    xls = pd.ExcelFile("/Users/or.hershko/Desktop/APT.-Scanner/data/scrapers/data.xlsx")
    df = xls.parse('2019')
    df.columns = df.iloc[1]
    df = df.drop([0, 1]).reset_index(drop=True)

    neighborhoods_raw = df[['name_shchuna']].dropna()
    neighborhoods_raw = neighborhoods_raw[neighborhoods_raw['name_shchuna'] != 'כלל העיר']

    unique_neighborhoods = sorted(set(neighborhoods_raw['name_shchuna']))

    # Initialize scraper
    api_key = os.getenv("SCRAPEOWL_API_KEY")
    if not api_key:
        raise ValueError("Missing SCRAPEOWL_API_KEY in environment variables.")
    scraper = MadlanScraper(api_key=api_key)

    results = []
    for name in unique_neighborhoods:
        print(f"Scraping: {name}...")
        try:
            data = scraper.scrape(neighborhood=name, city="תל אביב-יפו")
            data["שכונה"] = name
            results.append(data)
        except Exception as e:
            print(f"שגיאה עם שכונה {name}: {e}")
        time.sleep(2)  # polite delay

    with open("madlan_tlv_neighborhoods_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("✔ All done. Data saved to madlan_tlv_neighborhoods_data.json")

if __name__ == "__main__":
    main()