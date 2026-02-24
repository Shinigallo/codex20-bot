FROM node:20

WORKDIR /app

# Installiamo le dipendenze per Playwright (se serviranno per get_token.js)
RUN npx playwright install-deps

COPY package*.json ./
RUN npm install

# Copiamo tutto il codice, inclusi i dati 5etools scaricati
COPY . .

# Esponiamo la porta per Koyeb
EXPOSE 8080

CMD ["node", "bot.js"]
