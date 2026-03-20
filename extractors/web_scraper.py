"""
Web Scraper Module
Extracts structured content from URLs: title, headings, paragraphs, links, images, tables
No paid APIs - uses requests + BeautifulSoup + built-in summary
"""

import re
import urllib.request
import urllib.parse
import urllib.error
import html as html_lib
import json
from datetime import datetime


HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}


def fetch_url(url, timeout=15):
    """Fetch URL content with proper headers"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        import gzip
        with urllib.request.urlopen(req, timeout=timeout) as response:
            encoding = response.headers.get('Content-Encoding', '')
            content = response.read()
            
            if encoding == 'gzip':
                content = gzip.decompress(content)
            
            charset = 'utf-8'
            content_type = response.headers.get('Content-Type', '')
            if 'charset=' in content_type:
                charset = content_type.split('charset=')[-1].split(';')[0].strip()
            
            return content.decode(charset, errors='replace'), response.geturl()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch URL: {str(e)}")


def scrape_url(url):
    """Main scraping function - returns structured content"""
    try:
        from bs4 import BeautifulSoup
        
        start_time = datetime.now()
        html_content, final_url = fetch_url(url)
        
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove noise
        for tag in soup(['script', 'style', 'noscript', 'svg', 'iframe',
                        'nav', 'footer', 'aside', 'form', 'button',
                        'header', '[class*="cookie"]', '[class*="banner"]',
                        '[class*="popup"]', '[class*="modal"]', '[id*="cookie"]']):
            tag.decompose()
        
        # Title
        title = ""
        if soup.title:
            title = soup.title.string.strip() if soup.title.string else ""
        if not title:
            h1 = soup.find('h1')
            title = h1.get_text().strip() if h1 else ""
        
        # Meta description
        meta_desc = ""
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag and meta_tag.get('content'):
            meta_desc = meta_tag['content'].strip()
        
        # Author
        author = ""
        for selector in [
            {'name': 'author'},
            {'property': 'article:author'},
            {'name': 'twitter:creator'}
        ]:
            tag = soup.find('meta', attrs=selector)
            if tag and tag.get('content'):
                author = tag['content'].strip()
                break
        
        # Published date
        pub_date = ""
        for selector in [
            {'property': 'article:published_time'},
            {'name': 'date'},
            {'itemprop': 'datePublished'}
        ]:
            tag = soup.find('meta', attrs=selector)
            if tag and tag.get('content'):
                pub_date = tag['content'][:10]
                break
        
        # Headings hierarchy
        headings = []
        for level in range(1, 7):
            for h in soup.find_all(f'h{level}'):
                txt = h.get_text(separator=' ').strip()
                if txt:
                    headings.append({"level": level, "text": txt})
        
        # Main content extraction
        main_content = None
        for selector in ['main', 'article', '[role="main"]', '#content', 
                         '.content', '.article-body', '.post-content', 
                         '.entry-content', '#main-content']:
            el = soup.select_one(selector)
            if el:
                main_content = el
                break
        
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Paragraphs
        paragraphs = []
        for p in main_content.find_all('p'):
            txt = p.get_text(separator=' ').strip()
            if len(txt) > 30:
                paragraphs.append(txt)
        
        # Full clean text
        full_text = ' '.join(paragraphs)
        if not full_text:
            full_text = main_content.get_text(separator='\n')
            full_text = re.sub(r'\n{3,}', '\n\n', full_text).strip()
        
        # Links
        links = []
        seen_hrefs = set()
        base_domain = urllib.parse.urlparse(final_url).netloc
        
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if not href or href.startswith(('#', 'javascript:', 'mailto:')):
                continue
            if not href.startswith('http'):
                href = urllib.parse.urljoin(final_url, href)
            if href not in seen_hrefs:
                seen_hrefs.add(href)
                link_domain = urllib.parse.urlparse(href).netloc
                links.append({
                    "text": a.get_text(strip=True)[:80],
                    "href": href,
                    "external": link_domain != base_domain
                })
        
        # Images
        images = []
        for img in soup.find_all('img', src=True)[:20]:
            src = img['src']
            if not src.startswith('http'):
                src = urllib.parse.urljoin(final_url, src)
            alt = img.get('alt', '').strip()
            if src and not src.startswith('data:'):
                images.append({"src": src, "alt": alt})
        
        # Tables
        tables = []
        for table in soup.find_all('table')[:5]:
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
        
        # Word count
        word_count = len(full_text.split())
        
        # Summary using extractive algorithm
        from extractors.text_extractor import generate_summary
        summary = meta_desc if meta_desc else generate_summary(full_text, max_sentences=4)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        return {
            "success": True,
            "url": final_url,
            "original_url": url,
            "title": title,
            "author": author,
            "published_date": pub_date,
            "meta_description": meta_desc,
            "summary": summary,
            "paragraphs": paragraphs,
            "full_text": full_text,
            "headings": headings,
            "links": {
                "total": len(links),
                "internal": [l for l in links if not l['external']],
                "external": [l for l in links if l['external']],
            },
            "images": images,
            "tables": tables,
            "word_count": word_count,
            "scrape_time_seconds": round(elapsed, 2),
        }
    
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e),
        }


def scrape_multiple(urls):
    """Scrape multiple URLs and return aggregated results"""
    results = []
    for url in urls:
        url = url.strip()
        if url:
            results.append(scrape_url(url))
    return results
