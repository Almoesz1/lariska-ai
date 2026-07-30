const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

// Endpoint FastAPI lokal
const FASTAPI_BRIDGE_URL = 'http://127.0.0.1:8000/api/bridge/chat';

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    }
});

client.on('qr', (qr) => {
    console.log('\n==================================================');
    console.log(' SCAN QR CODE INI MENGGUNAKAN WHATSAPP DI HP KAMU:');
    console.log('==================================================\n');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('\n LARISKA AI WA Bridge SIAP!');
    console.log(' Terhubung ke FastAPI Sales Brain Engine.\n');
});

client.on('message', async (msg) => {
    // Abaikan grup, status/broadcast WA, pesan dari bot sendiri, atau pesan kosong
    if (
        msg.from.includes('@g.us') || 
        msg.from.includes('@broadcast') || 
        msg.fromMe || 
        !msg.body || 
        !msg.body.trim()
    ) {
        return;
    }

    console.log(`📩 [Pesan Masuk] dari ${msg.from}: "${msg.body}"`);

    try {
        const response = await axios.post(FASTAPI_BRIDGE_URL, {
            user_message: msg.body,
            sender_id: msg.from,
            product_name: "Sepatu Sneakers Lariska",
            product_price: 450000
        });

        const replyText = response.data.reply;

        if (replyText) {
            await msg.reply(replyText);
            console.log(`🤖 [Sales Brain Balas]: "${replyText}"\n`);
        }
    } catch (error) {
        if (error.response) {
            console.error(`❌ FastAPI Error (${error.response.status}): Cek Terminal Uvicorn Python!`);
        } else {
            console.error('❌ Gagal menghubungi FastAPI:', error.message);
        }
    }
});

// Tangani error yang tidak terduga agar aplikasi tidak langsung mati
process.on('unhandledRejection', (reason, promise) => {
    console.log(' [Warning] Unhandled Rejection:', reason.message || reason);
});

client.initialize();