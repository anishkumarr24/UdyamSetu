import requests
from PIL import Image
import io

img = Image.new('RGB', (100, 100), color = 'white')
buf = io.BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)

res = requests.post('http://localhost:8000/api/v1/ocr/extract', files={'file': ('test.jpg', buf, 'image/jpeg')})
print(res.status_code)
print(res.json())
