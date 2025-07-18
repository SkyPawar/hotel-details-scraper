from flask import Flask, render_template, request, send_file
from scraper_final import AdvancedHotelScraper
import os
from datetime import datetime

app = Flask(__name__)
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    city = request.form['city']
    country = request.form['country']
    motel_type = request.form['type']

    scraper = AdvancedHotelScraper(use_selenium=True)
    scraper.load_proxies()

    try:
        hotels = scraper.scrape_all_sources(city, country)
        hotels = scraper.remove_duplicates(hotels)

        filename = f"hotels_{city}_{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filename = filename.replace(' ', '_')
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        scraper.save_to_csv(hotels, file_path)

        return {"status": "success", "message": f"Scraping done! File saved as {filename}"}

    finally:
        scraper.cleanup()

if __name__ == '__main__':
    app.run(debug=True)
