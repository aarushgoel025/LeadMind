FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Mock ArmorClaw CLI installation
RUN echo '#!/bin/bash\necho "{\"findings\": []}"' > /usr/local/bin/armorclaw && chmod +x /usr/local/bin/armorclaw

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
