// React'in geliştirme sırasında bazı sorunları daha görünür yapmasını sağlar.
import { StrictMode } from 'react'
// React uygulamasını sayfaya basmak için gereken fonksiyon.
import { createRoot } from 'react-dom/client'
// Bizim ana ekran bileşenimiz.
import App from './App.tsx'
// Global CSS dosyamız.
import './index.css'

// HTML içindeki `root` elemanını bul.
// `!` işareti TypeScript'e "bu eleman kesin var" demek.
createRoot(document.getElementById('root')!).render(
  // StrictMode, sadece geliştirme sırasında ekstra kontroller yapar.
  <StrictMode>
    {/* Ekranda göstereceğimiz ana React bileşeni App */}
    <App />
  </StrictMode>,
)
