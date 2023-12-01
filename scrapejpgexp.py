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

model = EdsrModel.from_pretrained('eugenesiow/edsr-base', scale=2)      # scale 2, 3 and 4 models available

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
            () => {
                const links = [];
                const elements = document.querySelectorAll('.rg_i');
                for (const element of elements) {
                    links.push(element.getAttribute('src'));
                }
                return links;
            }
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


def transform_image(image_path):
    img = Image.open(image_path)

    if img.mode != 'RGB':
        img = img.convert('RGB')

    transform = transforms.Compose([
        transforms.ToTensor(),
    ])
    return transform(img)



def save_image(tensor, filename):
    tensor = tensor.clamp(0, 1)  # Pastikan nilai tensor dalam rentang [0, 1]
    img = F.to_pil_image(tensor)
    img.save(filename)


def enhance_image_quality(image_path):
    # Membaca gambar
    image = cv2.imread(image_path)
    denoised_image = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    # Menerapkan teknik peningkatan kualitas
    kernel_sharpening = np.array([[-1, -1, -1],
                              [-1, 9, -1],
                              [-1, -1, -1]])

    sharpened_image = cv2.filter2D(denoised_image, -1, kernel_sharpening)

    # Menyimpan gambar hasil
    cv2.imwrite(image_path, sharpened_image)

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

                # enhance_image_quality(screenshot_path)

                # Buka gambar dengan Pillow
                img_tensor = transform_image(screenshot_path)
                img_tensor = img_tensor.unsqueeze(0)  # Tambahkan dimensi batch

                with torch.no_grad():  # Nonaktifkan perhitungan gradient
                    preds = model(img_tensor)
                    preds = preds.squeeze(0)  # Hapus dimensi batch

                save_image(preds, f'{folder}/{filename}')
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
