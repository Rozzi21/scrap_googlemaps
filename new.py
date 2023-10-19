from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import argparse
import re


@dataclass
class Business:
    "holds business data"

    name: str = None
    address: str = None
    website: str = None
    phone_number: str = None
    reviews_count: int = None
    reviews_average: float = None
    latitude: str = None
    longitude: str = None


@dataclass
class BusinessList:
    "list_daftar"

    business_list: list[Business] = field(default_factory=list)

    def dataframe(self):
        "jadi data frame"

        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        "simpan data ke xlsx"

        self.dataframe().to_excel(f"{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        "simpan ke file csv"

        self.dataframe().to_csv(f"{filename}.csv", index=False)


def main(search_queries_with_counts):
    business_list = BusinessList()
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            for search_for, count in search_queries_with_counts:
                page.goto("https://www.google.com/maps", timeout=60000)

                page.locator('//input[@id="searchboxinput"]').fill(search_for)
                page.wait_for_timeout(3000)

                page.keyboard.press("Enter")
                page.wait_for_timeout(5000)

                # Scraping the data from Google Maps based on the count
                for i in range(count):
                    # Using the provided scraping logic
                    listing = page.locator(f'//div[@data-result-index="{i}"]')
                    listing.click()
                    page.wait_for_timeout(5000)

                    # Extracting coordinates from script content
                    script_content = page.locator('/html/head/script[2]').inner_text()
                    coordinates_pattern = re.compile(r'@(-?\d+\.\d+),(-?\d+\.\d+)')
                    matches = coordinates_pattern.search(script_content)
                    if matches:
                        latitude, longitude = matches.groups()
                    else:
                        latitude, longitude = None, None

                    # Rest of the scraping logic...
                    name_xpath = '//div[contains(@class, "fontHeadlineSmall")]'
                    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                    website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
                    phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
                    reviews_span_xpath = '//span[@role="img" and contains(@aria-label, "Bintang")]'
                    business = Business()

                    reviews_elements = listing.locator(reviews_span_xpath).all()

                    if listing.locator(name_xpath).count() > 0:
                        business.name = listing.locator(name_xpath).inner_text()
                    if listing.locator(address_xpath).count() > 0:
                        business.address = listing.locator(address_xpath).inner_text()
                    if listing.locator(website_xpath).count() > 0:
                        business.website = listing.locator(website_xpath).inner_text()
                    if listing.locator(phone_number_xpath).count() > 0:
                        business.phone_number = listing.locator(phone_number_xpath).inner_text()
                    if reviews_elements:
                        review_element = reviews_elements[0]
                        aria_label = review_element.get_attribute("aria-label")
                        business.reviews_average = float(aria_label.split()[1].replace(",", ".").strip())
                        business.reviews_count = int(aria_label.replace(".", "").split()[2].strip())

                    business.latitude = latitude
                    business.longitude = longitude

                    business_list.business_list.append(business)

                # Save the scraped data to files
                business_list.save_to_excel(f'google_maps_{"_".join([query for query, _ in search_queries_with_counts])}')
                business_list.save_to_csv(f'google_maps_{"_".join([query for query, _ in search_queries_with_counts])}')

            browser.close()
            
    except Exception as e:
        print("Terjadi kesalahan:", str(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--queries", type=str, nargs='+', help="List of search queries with counts, e.g., 'kopiniboss malang:10'")
    args = parser.parse_args()

    # Handle search queries input
    if args.queries:
        # Split each query by ':' to get the query and count
        search_queries_with_counts = [(query.split(':')[0], int(query.split(':')[1])) for query in args.queries]
    else:
        # Default search query and count if none is provided
        search_queries_with_counts = [("kopiniboss malang", 10)]

    main(search_queries_with_counts)
    print("selesai cuy")