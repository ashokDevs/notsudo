import type { Metadata } from "next"
import { Press_Start_2P, VT323, Inter } from "next/font/google"
import "./globals.css"
import { Analytics } from "@vercel/analytics/react"

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-modern"
})

const pressStart2P = Press_Start_2P({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-retro-heading"
})

const vt323 = VT323({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-retro-body"
})

export const metadata: Metadata = {
  title: "NotSudo - AI-Powered Code Automation",
  description: "Transform GitHub issues into production-ready pull requests with AI-powered code automation",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${pressStart2P.variable} ${vt323.variable} font-sans`}>{children}<Analytics /></body>
    </html>
  )
}
