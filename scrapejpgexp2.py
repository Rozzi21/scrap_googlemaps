import csv
import os
import asyncio
import torch
import cv2
import numpy as np
from PIL import Image
from torchvision import transforms
import torchvision.transforms.functional as F
from super_image import EdsrModel
from playwright.async_api import async_playwright, TimeoutError
from urllib.parse import urlparse

async def scrape_images(query):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        print(f"Memulai scraping untuk query: {query}")

        # Membuka Google Images
        await page.goto(f'https://www.google.com/search?q={query}&tbm=isch',timeout=60000)

        image_links = []

        # Menggulir halaman beberapa kali untuk memuat lebih banyak gambar
        for _ in range(10):  # Menggulir 10 kali, Anda bisa menyesuaikan jumlahnya
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2) 
        # Menyimpan semua link gambar dalam variabel
        image_links = await page.evaluate('''
            (async () => { // Ubah fungsi ini menjadi fungsi async
                const links = [];
                const elements = document.querySelectorAll('.rg_i');
                for (const element of elements) {
                    element.click(); // Simulate click
                    await new Promise(resolve => setTimeout(resolve, 2000)); // Sekarang ini bekerja karena fungsi adalah async
                    const highResImage = document.querySelector('[role="link"] img[aria-hidden="false"]'); 
                    if (highResImage) {
                        links.push(highResImage.getAttribute('src'));
                    }
                    // Logic untuk menutup drawer dan berpindah ke gambar berikutnya
                }
                return links;
            })()
        ''')


        await browser.close()

        #batasi jumlah gambar maksimum menjadi 100
        if len(image_links) > 300:
            image_links = image_links[:300]

        # Buat folder sesuai dengan query
        folder_name = query.replace(' ', '_')
        os.makedirs(folder_name, exist_ok=True)

        print(f"Menyimpan gambar untuk query: {query}")

        # Download dan simpan gambar dalam folder
        valid_links = [link for link in image_links if is_valid_url(link)]
        for i, link in enumerate(valid_links, start=1):
            await download_image(link, folder_name, f'{query}_{i}.jpg')


async def download_image(url, folder, filename):

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        if is_valid_url(url):
            try:
                await page.goto(url, timeout=60000)
                print(f"Downloading {filename}")
                screenshot_path = f'{folder}/{filename}'
                await page.locator("img").screenshot(path=screenshot_path)
                img = screenshot_path
                img.save(f'{folder}/{filename}')
            except TimeoutError:
                print(f"Timeout ketika mengakses {url}. Melanjutkan ke link berikutnya.")
            finally: 
                await browser.close()

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

if __name__ == "__main__":
    with open('query.csv', 'r') as csv_file:
        reader = csv.reader(csv_file)
        queries = list(reader)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*(scrape_images(query[0]) for query in queries)))

print("selesai")
