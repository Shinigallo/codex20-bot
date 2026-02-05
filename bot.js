const { Telegraf } = require('telegraf');
const Groq = require('groq-sdk');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const bot = new Telegraf(process.env.TELEGRAM_TOKEN);
const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
const AUTHORIZED_USER_ID = process.env.AUTHORIZED_USER_ID;

// Caricamento Contesto (Codex20 Personality)
let systemContext = "Sei Codex20, un assistente digitale evoluto. Rispondi in italiano.\n";
try {
  const contextDir = path.join(__dirname, 'data');
  ['SOUL.md', 'IDENTITY.md', 'USER.md'].forEach(file => {
    const filePath = path.join(contextDir, file);
    if (fs.existsSync(filePath)) {
        systemContext += `\nINFORMAZIONI DA ${file}:\n${fs.readFileSync(filePath, 'utf8')}\n`;
    }
  });
} catch (e) { console.error("Errore contesto:", e); }

bot.on('text', async (ctx) => {
    if (AUTHORIZED_USER_ID && ctx.from.id.toString() !== AUTHORIZED_USER_ID.toString()) return;

    await ctx.sendChatAction('typing');

    try {
        const chatCompletion = await groq.chat.completions.create({
            messages: [
                { role: 'system', content: systemContext },
                { role: 'user', content: ctx.message.text }
            ],
            model: 'llama-3.3-70b-versatile', // Modello potentissimo e veloce
            temperature: 0.7,
            max_tokens: 2048,
        });

        let response = chatCompletion.choices[0]?.message?.content || "Codex20 non ha prodotto risposta.";
        response += "\n\n🎲";
        
        if (response.length > 4000) {
            await ctx.reply(response.substring(0, 4000));
        } else {
            await ctx.reply(response, { parse_mode: 'Markdown' }).catch(() => ctx.reply(response));
        }
    } catch (error) {
        console.error("Errore Groq:", error);
        ctx.reply("Spiacente, Codex20 ha avuto un glitch di comunicazione con i server Groq. 🎲");
    }
});

bot.launch();
console.log('Codex20 Bot attivo!');