FROM node:20-alpine

RUN apk add --no-cache python3 make g++

WORKDIR /app

COPY package*.json ./
RUN npm install

# Copiamo tutto il codice e i file di contesto
COPY . .

# Il comando rimarrà lo stesso, ma i file saranno dentro /app/context
CMD ["node", "bot.js"]
