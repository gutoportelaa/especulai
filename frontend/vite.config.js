import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// GitHub Pages serve o site em /<repo>/, não na raiz. `base` precisa casar com
// isso senão os assets são pedidos em / e voltam 404. Sobrescrevível por
// VITE_BASE para publicar em domínio próprio ou na raiz ("/").
export default defineConfig({
  base: process.env.VITE_BASE || '/',
  plugins: [react()],
})
