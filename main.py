from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import argparse
@dataclass
class Business:
    "bussines data"

    name: str = None
    address: str = None
    # sc
    website: str = None
    phone_number: str = None
    reviews_count: int = None
    reviews_average: float = None
    latitude: float = None
    longitude: float = None
    comments: str = None

@dataclass
class Comment:
    comment: str = None


@dataclass
class BusinessList:
    """listing data dari object bussines dan di buat xlsx dan csv"""

    business_list: list[Business] = field(default_factory=list)

    def dataframe(self):
        """transform business_list to pandas dataframe

        Returns: pandas dataframe
        """
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        """saves pandas dataframe to excel (xlsx) file

        Args:
            filename (str): filename
        """
        self.dataframe().to_excel(f"{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        """saves pandas dataframe to csv file

        Args:
            filename (str): filename
        """
        self.dataframe().to_csv(f"{filename}.csv", index=False)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.google.com/maps", timeout=60000)
        # wait is added for dev phase. can remove it in production
        page.wait_for_timeout(5000)

        page.locator('//input[@id="searchboxinput"]').fill(search_for)
        page.wait_for_timeout(3000)

        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)

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
                print(f"Total: {len(listings)}")
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
        print("mulai scrapping")
        for listing in listings:
            listing.click()
            page.wait_for_timeout(5000)

            name_xpath = '//div[contains(@class, "fontHeadlineSmall")]'
            address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
            website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
            phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
            reviews_span_xpath = '//span[@role="img" and contains(@aria-label, "Bintang")]'
            # ambil review harus loop berdasarkan listing
            # reviews_name_xpath = '//button[contains(@jsaction, "reviewerLink")]'
            button_ulasan_xpath ='//button[@role="tab" and contains(., "Ulasan")]'

            reviews_elements = listing.locator(reviews_span_xpath).all()

            business = Business()

            if listing.locator(name_xpath).count() > 0:
                business.name = listing.locator(name_xpath).inner_text()
            else:
                business.name = ""
            if page.locator(address_xpath).count() > 0:
                business.address = page.locator(address_xpath).inner_text()
            else:
                business.address = ""
            if page.locator(website_xpath).count() > 0:
                business.website = page.locator(website_xpath).inner_text()
            else:
                business.website = ""
            if page.locator(phone_number_xpath).count() > 0:
                business.phone_number = page.locator(phone_number_xpath).inner_text()
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

            business_list.business_list.append(business)

        print("Mencoba menggambil latitude dan longitude")

        for business in business_list.business_list:
            name = business.name
            address = business.address
            page.locator('//input[@id="searchboxinput"]').fill(name + " " + address)
            page.wait_for_timeout(3000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)

            current_url = page.url
            latitude, longitude = current_url.split('@')[1].split(',')[0:2]
            business.latitude = latitude
            business.longitude = longitude
            page.wait_for_timeout(3000)
            
        print("Mencoba menggambil comment pada setiap bussines")

        for business in business_list.business_list:
            page.locator('//input[@id="searchboxinput"]').fill(name + " " + address)
            page.wait_for_timeout(3000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)
            page.get_by_label("Ulasan untuk").click()
            page.wait_for_timeout(3000)
            comment_elements = page.locator('//div[@class="MyEned"]').all()
            comments_value = []
            for element in comment_elements:
                # Temukan elemen <span> dalam elemen "MyEned" menggunakan XPath relatif
                span_element = element.locator('//span[@class="wiI7pd"]').first
                # Ambil teks dari elemen <span>
                if span_element:
                    span_text = span_element.inner_text()
                    print("Review Text:", span_text)
                    comments_value.append(span_text)
            business.comments = comments_value
            
        business_list.save_to_excel(search_for)
        business_list.save_to_csv(search_for)
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", type=str)
    parser.add_argument("-t", "--total", type=int)
    args = parser.parse_args()

    if args.search:
        search_for = args.search
    else:
        # in case no arguments passed
        # the scraper will search by defaukt for:
        search_for = "kampus stimata"

    # total number of products to scrape. Default is 10
    if args.total:
        total = args.total
    else:
        total = 10

    main()