FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Change vite port to 3000
RUN sed -i 's/"dev": "vite"/"dev": "vite --port 3000 --host 0.0.0.0"/' package.json

CMD ["npm", "run", "dev"]
