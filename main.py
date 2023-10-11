from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import argparse


@dataclass
class Business:
    """holds business data"""

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
        """jadi data frame

        Returns: pandas dataframe
        """
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        """simpan data ke xlsx

        Args:
            filename (str): filename
        """
        self.dataframe().to_excel(f"{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        """simpan ke file csv

        Args:
            filename (str): filename
        """
        self.dataframe().to_csv(f"{filename}.csv", index=False)


def main():
    try:
     with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        for search_for in search_queries:
            page.goto("https://www.google.com/maps", timeout=60000)

            page.locator('//input[@id="searchboxinput"]').fill(search_for)
            page.wait_for_timeout(3000)

            page.keyboard.press("Enter")
            page.wait_for_timeout(5000)

        # scrolling
        page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')

        # this variable is used to detect if the bot
        # scraped the same number of listings in the previous iteration
        previously_counted = 0
        while True:
            page.mouse.wheel(0, 10000)
            page.wait_for_timeout(3000)

            if (
                page.locator(
                    '//a[contains(@href, "https://www.google.com/maps/place")]'
                ).count()
                >= total
            ):
                listings = page.locator(
                    '//a[contains(@href, "https://www.google.com/maps/place")]'
                ).all()[:total]
                listings = [listing.locator("xpath=..") for listing in listings]
                print(f"Total Scraped: {len(listings)}")
                break
            else:
                # logic to break from loop to not run infinitely
                # in case arrived at all available listings
                if (
                    page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).count()
                    == previously_counted
                ):
                    listings = page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).all()
                    print(f"Arrived at all available\nTotal Scraped: {len(listings)}")
                    break
                else:
                    previously_counted = page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).count()
                    print(
                        f"Currently Scraped: ",
                        page.locator(
                            '//a[contains(@href, "https://www.google.com/maps/place")]'
                        ).count(),
                    )

        business_list = BusinessList()

        # scraping
        for listing in listings:
            listing.click()
            page.wait_for_timeout(5000)

            name_xpath = '//div[contains(@class, "fontHeadlineSmall")]'
            address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
            website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
            phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
            reviews_span_xpath = '//span[@role="img" and contains(@aria-label, "Bintang")]'
            latitude_longitude_xpath ='//button[@jsaction="reveal.card.latLng")]'
            business = Business()

            print("Clicking on:", listing.locator(name_xpath).inner_text())
            # print("coordinates", listing.locator(latitude_longitude_xpath).inner_text())
            reviews_elements = listing.locator(reviews_span_xpath).all()

            if listing.locator(name_xpath).count() > 0:
                business.name = listing.locator(name_xpath).inner_text()
            else:
                business.name = ""
            if listing.locator(address_xpath).count() > 0:
                business.address = listing.locator(address_xpath).inner_text()
            else:
                business.address = ""
            if listing.locator(website_xpath).count() > 0:
                business.website = listing.locator(website_xpath).inner_text()
            else:
                business.website = ""
            if listing.locator(phone_number_xpath).count() > 0:
                business.phone_number = listing.locator(phone_number_xpath).inner_text()
            else:
                business.phone_number = ""
            if reviews_elements:
                review_element = reviews_elements[0]
                aria_label = review_element.get_attribute("aria-label")
                business.reviews_average = float(aria_label.split()[1].replace(",", ".").strip())
                business.reviews_count = int(aria_label.replace(".", "").split()[2].strip())
            else:
                business.reviews_average = ""
                business.reviews_count = ""

            if listing.locator(latitude_longitude_xpath).count() > 0:
                coordinates = listing.locator(latitude_longitude_xpath).inner_text()
                latitude, longitude = coordinates.split(', ')
                business.latitude = latitude
                business.longitude = longitude
            else:
                
            # Jika tidak ditemukan elemen dengan koordinat, ambil dari URL
                current_url = page.url
                latitude, longitude = current_url.split('@')[1].split(',')[0:2]
                business.latitude = latitude
                business.longitude = longitude

            business_list.business_list.append(business)

        # simpan ke file xlsx/csv
        business_list.save_to_excel(f'google_maps {args.search}')
        business_list.save_to_csv(f'google_maps {args.search}')

        browser.close()
        
    except Exception as e:
        print("Terjadi kesalahan:", str(e))



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--queries", type=str, nargs='+', help="List of search queries")
    parser.add_argument("-t", "--total", type=int)
    args = parser.parse_args()

    if args.search:
        search_for = args.search
    else:
        #otomatis search ini jika kosong
        search_for = "kopiniboss malang"

    # total yang mau di cari
    if args.total:
        total = args.total
    else:
        total = 10

    main()

    print("selesai cuy")