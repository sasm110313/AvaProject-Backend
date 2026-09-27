import os
import sys
import re
import json
import time
import socket
import logging
from urllib.parse import urljoin, urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(DATA_DIR, 'scraper.log')
IMAGES_DIR = os.path.join(DATA_DIR, 'images')
URLS_FILE = os.path.join(DATA_DIR, 'product_urls.json')
OUTPUT_FILE = os.path.join(DATA_DIR, 'products.json')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]
)

orig_getaddrinfo = socket.getaddrinfo
def custom_getaddrinfo(host, port, *args, **kwargs):
    if host == 'echoseyyed.co':
        return orig_getaddrinfo('89.42.136.2', port, *args, **kwargs)
    return orig_getaddrinfo(host, port, *args, **kwargs)
socket.getaddrinfo = custom_getaddrinfo

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'fa,en-US;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
}

os.makedirs(IMAGES_DIR, exist_ok=True)

def create_session():
    s = requests.Session()
    retries = Retry(
        total=1,
        connect=1,
        read=0,
        status=0,
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=5, pool_maxsize=5)
    s.mount('https://', adapter)
    s.mount('http://', adapter)
    s.headers.update(HEADERS)
    return s

def download_image(session, img_url, dest_folder):
    if not img_url or img_url.startswith('data:') or 'placeholder' in img_url:
        return None
    try:
        parsed = urlparse(img_url)
        filename = os.path.basename(parsed.path)
        if not filename or '.' not in filename:
            filename = f"img_{int(time.time()*1000)}.jpg"
        filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
        dest_path = os.path.join(dest_folder, filename)
        
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 500:
            return os.path.relpath(dest_path, DATA_DIR)
            
        r = session.get(img_url, timeout=12, stream=True)
        if r.status_code == 200:
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=16384):
                    if chunk:
                        f.write(chunk)
            return os.path.relpath(dest_path, DATA_DIR)
    except Exception as e:
        logging.debug(f"Image skip {img_url}: {e}")
    return None

def parse_product_page(session, prod_info):
    url = prod_info['url']
    try:
        r = session.get(url, timeout=15)
    except Exception as e:
        logging.warning(f"Timeout/Error fetching {url}: {e}")
        return None

    if r.status_code != 200:
        logging.warning(f"Status {r.status_code} for {url}")
        return None
    
    soup = BeautifulSoup(r.text, 'html.parser')
    
    title_el = soup.find('h1', class_='product-title') or soup.find('h1')
    title = title_el.get_text(strip=True) if title_el else ''
    if not title:
        return None
    
    slug = url.strip('/').split('/')[-1]
    
    price_el = soup.select_one('.summary .price, .product-info .price, p.price, .price-wrapper')
    price_str = price_el.get_text(' ', strip=True) if price_el else ''
    price_amount = None
    currency = None
    if 'تومان' in price_str:
        currency = 'تومان'
    elif 'ریال' in price_str:
        currency = 'ریال'
    
    digits = re.findall(r'[\d,]+', price_str.replace('٬', ','))
    if digits:
        clean_digit = digits[-1].replace(',', '')
        if clean_digit.isdigit():
            price_amount = int(clean_digit)

    stock_status = 'موجود'
    summary_el = soup.select_one('.product-summary, .product-info, .summary.entry-summary')
    if summary_el:
        stock_el = summary_el.select_one('.stock, .availability')
        if stock_el:
            stxt = stock_el.get_text(strip=True)
            if 'ناموجود' in stxt or 'عدم موجودی' in stxt or 'out-of-stock' in stock_el.get('class', []):
                stock_status = 'ناموجود'
            elif 'موجود' in stxt:
                stock_status = 'موجود'
            else:
                stock_status = stxt
        elif 'برای خرید تماس بگیرید' in price_str:
            stock_status = 'تماس بگیرید'
    elif 'برای خرید تماس بگیرید' in price_str:
        stock_status = 'تماس بگیرید'
    
    sku_el = soup.select_one('.sku_wrapper .sku, .sku')
    sku = sku_el.get_text(strip=True) if sku_el else ''
    
    breadcrumbs = []
    for b in soup.select('.breadcrumbs a, .woocommerce-breadcrumb a'):
        txt = b.get_text(strip=True)
        if txt and txt not in ['خانه', 'Home']:
            breadcrumbs.append(txt)
            
    short_desc_el = soup.select_one('.woocommerce-product-details__short-description, .product-short-description')
    short_description = short_desc_el.get_text('\n', strip=True) if short_desc_el else ''
    
    desc_el = soup.select_one('#tab-description, .woocommerce-Tabs-panel--description')
    description_text = desc_el.get_text('\n', strip=True) if desc_el else ''
    description_html = str(desc_el) if desc_el else ''
    
    specs = {}
    for table in soup.select('table.woocommerce-product-attributes, table.shop_attributes, .tab-specification table'):
        for row in table.find_all('tr'):
            th = row.find(['th', 'label'])
            td = row.find('td')
            if th and td:
                k = th.get_text(strip=True)
                v = td.get_text(strip=True)
                if k and v:
                    specs[k] = v
            else:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    k = cells[0].get_text(strip=True)
                    v = cells[1].get_text(strip=True)
                    if k and v:
                        specs[k] = v

    remote_images = []
    seen_imgs = set()
    gallery_selectors = [
        '.woocommerce-product-gallery__image a',
        '.woocommerce-product-gallery__image img',
        '.product-images img',
        '.woocommerce-product-gallery img'
    ]
    for sel in gallery_selectors:
        for el in soup.select(sel):
            img_url = el.get('href') or el.get('data-large_image') or el.get('data-src') or el.get('src')
            if img_url:
                img_url = urljoin(url, img_url)
                if img_url not in seen_imgs and not img_url.startswith('data:') and 'placeholder' not in img_url:
                    if any(img_url.lower().endswith(ext) or ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.svg']):
                        seen_imgs.add(img_url)
                        remote_images.append(img_url)

    prod_img_folder = os.path.join(IMAGES_DIR, slug)
    os.makedirs(prod_img_folder, exist_ok=True)
    
    local_images = []
    for img_url in remote_images[:3]:
        local_path = download_image(session, img_url, prod_img_folder)
        if local_path:
            local_images.append(local_path)
            
    product_data = {
        'title': title,
        'slug': slug,
        'url': url,
        'category_key': prod_info.get('category_key', ''),
        'category_name': prod_info.get('category_name', ''),
        'breadcrumbs': breadcrumbs,
        'sku': sku,
        'price': price_str,
        'price_amount': price_amount,
        'currency': currency,
        'stock_status': stock_status,
        'short_description': short_description,
        'description': description_text,
        'description_html': description_html,
        'specifications': specs,
        'image_urls': remote_images,
        'local_images': local_images
    }
    return product_data

def main():
    logging.info("Starting reliable sequential scraper for echoseyyed.co...")
    
    if not os.path.exists(URLS_FILE):
        logging.error("URLS_FILE does not exist!")
        return

    with open(URLS_FILE, 'r', encoding='utf-8') as f:
        items = json.load(f)
    logging.info(f"Loaded {len(items)} total products from {URLS_FILE}")
    
    existing_products = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                for p in saved:
                    if p.get('url') and p.get('title'):
                        existing_products[p['url']] = p
            logging.info(f"Resuming with {len(existing_products)} already scraped products.")
        except Exception as e:
            logging.warning(f"Could not load existing products: {e}")

    session = create_session()
    
    for idx, item in enumerate(items, 1):
        url = item['url']
        if url in existing_products and existing_products[url].get('title'):
            continue
            
        t0 = time.time()
        prod_data = parse_product_page(session, item)
        elapsed = round(time.time() - t0, 1)
        
        if prod_data and prod_data.get('title'):
            existing_products[url] = prod_data
            logging.info(f"[{len(existing_products)}/{len(items)}] OK ({elapsed}s): '{prod_data['title']}' | Specs: {len(prod_data['specifications'])} | Imgs: {len(prod_data['local_images'])}")
            
            # Save immediately on every product!
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(existing_products.values()), f, ensure_ascii=False, indent=2)
        else:
            logging.warning(f"[{len(existing_products)}/{len(items)}] Skipped/Empty ({elapsed}s): {url}")
            
        time.sleep(0.3)

    logging.info(f"ALL COMPLETE! Total scraped products: {len(existing_products)}")

if __name__ == '__main__':
    main()
