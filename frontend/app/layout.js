import { Inter } from "next/font/google";
import Navigation from "./components/Navigation";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "Job Application Assistant",
  description: "AI-powered job application and cover letter generator",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
          <Navigation />
          <main className="py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
