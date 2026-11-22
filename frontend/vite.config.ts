import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import tailwind from '@tailwindcss/vite';
import {Agent} from 'node:http';
// Reuse backend sockets during thousands of sequential PNG uploads.
const agent=new Agent({keepAlive:true,maxSockets:8,maxFreeSockets:4});
const proxy={target:'http://127.0.0.1:8001',agent};
export default defineConfig({plugins:[react(),tailwind()],server:{proxy:{'/api':proxy,'/assets':proxy}}});
