const { Telegraf } = require('telegraf');
const { GoogleGenerativeAI } = require('@google/generative-ai');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

// Health Check Server per Koyeb
require('./healthcheck.js');

const bot = new Telegraf(process.env.TELEGRAM_TOKEN);
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });

const AUTHORIZED_USER_ID = process.env.AUTHORIZED_USER_ID;

// Caricamento Contesto Base (Codex20 Personality)
let systemContextBase = "Sei Codex20, un assistente digitale evoluto e Dungeon Master esperto. Rispondi in italiano.\n";
try {
  const contextDir = path.join(__dirname, 'data');
  const filesToRead = ['SOUL.md', 'IDENTITY.md', 'USER.md'];
  filesToRead.forEach(file => {
    const filePath = path.join(contextDir, file);
    if (fs.existsSync(filePath)) {
        const content = fs.readFileSync(filePath, 'utf8');
        systemContextBase += `\nINFORMAZIONI DA ${file}:\n${content}\n`;
    }
  });
} catch (e) { 
  console.error("Errore caricamento contesto:", e); 
}

// Funzione ricorsiva per cercare file JSON
function getAllFiles(dirPath, arrayOfFiles) {
  const files = fs.readdirSync(dirPath);
  arrayOfFiles = arrayOfFiles || [];

  files.forEach(function(file) {
    if (fs.statSync(dirPath + "/" + file).isDirectory()) {
      arrayOfFiles = getAllFiles(dirPath + "/" + file, arrayOfFiles);
    } else {
      if (file.endsWith('.json')) {
        arrayOfFiles.push(path.join(dirPath, "/", file));
      }
    }
  });

  return arrayOfFiles;
}

// Funzione per cercare nei JSON di 5etools
function search5etools(query) {
    const dataDir = path.join(__dirname, 'data', '5etools');
    if (!fs.existsSync(dataDir)) return "";

    let foundData = "";
    try {
        const allFiles = getAllFiles(dataDir);
        const keywords = query.toLowerCase().split(' ').filter(k => k.length > 3);

        if (keywords.length === 0) return "";

        for (const filePath of allFiles) {
            try {
                const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
                const keys = Object.keys(content).filter(k => !['_meta', 'linkedFile'].includes(k));
                
                for (const key of keys) {
                    const collection = content[key];
                    if (Array.isArray(collection)) {
                        for (const item of collection) {
                            if (item.name && keywords.some(k => item.name.toLowerCase().includes(k))) {
                                foundData += `\n[${key.toUpperCase()} - ${path.basename(filePath)}]:\n${JSON.stringify(item, null, 2)}\n`;
                                if (foundData.length > 8000) break;
                            }
                        }
                    }
                    if (foundData.length > 8000) break;
                }
            } catch (e) { }
            if (foundData.length > 8000) break;
        }
    } catch (e) { 
        console.error("Errore ricerca 5etools:", e);
    }

    return foundData ? `\n\nDATI TECNICI DA 5ETOOLS:\n${foundData}` : "";
}

bot.on('text', async (ctx) => {
    if (AUTHORIZED_USER_ID && ctx.from.id.toString() !== AUTHORIZED_USER_ID.toString()) return;

    await ctx.sendChatAction('typing');

    const userQuery = ctx.message.text;
    const additionalContext = search5etools(userQuery);
    const finalPrompt = `${systemContextBase}${additionalContext}\n\nUtente: ${userQuery}`;

    try {
        const result = await model.generateContent(finalPrompt);
        const responseText = result.response.text();

        let response = responseText || "Codex20 non ha prodotto risposta.";
        response += "\n\n🎲";
        
        if (response.length > 4000) {
            await ctx.reply(response.substring(0, 4000));
        } else {
            await ctx.reply(response, { parse_mode: 'Markdown' }).catch(() => ctx.reply(response));
        }
    } catch (error) {
        console.error("Errore Gemini:", error);
        ctx.reply("Spiacente, Codex20 ha avuto un glitch di comunicazione con i server Gemini. 🎲");
    }
});

bot.launch();
console.log('Codex20 Bot attivo con Gemini (2.0 Flash)!');
