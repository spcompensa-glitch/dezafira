import { Inter } from "next/font/google";
import fs from 'fs';
import path from 'path';

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata = {
  title: 'Open Generative AI — Free AI Image & Video Studio',
  description: 'Generate AI images and videos using 200+ models — Flux, Midjourney, Kling, Veo, Seedance and more.',
};

export default function RootLayout({ children }) {
  // Read the CSS file synchronously to inject it (works in Server Components)
  const cssPath = path.join(process.cwd(), 'app', 'globals.css');
  let cssContent = '';
  try {
    cssContent = fs.readFileSync(cssPath, 'utf-8');
  } catch (e) {
    console.warn('Could not read globals.css');
  }

  return (
    <html lang="en">
      <head>
        <script src="https://cdn.tailwindcss.com"></script>
        <style dangerouslySetInnerHTML={{ __html: cssContent }} />
      </head>
      <body className={inter.variable}>{children}</body>
    </html>
  );
}
