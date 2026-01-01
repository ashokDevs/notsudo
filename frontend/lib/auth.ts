/**
 * Better Auth - Server Configuration
 * Using Better Auth's built-in PostgreSQL adapter (Kysely-based)
 * No external ORM required - Better Auth handles schema and migrations
 */
import { betterAuth } from "better-auth";
import { Pool } from "pg";

// Debug logging
const databaseUrl = process.env.DATABASE_URL;
console.log("[Auth Debug] Initializing Better Auth...");
console.log("[Auth Debug] DATABASE_URL exists:", !!databaseUrl);
console.log("[Auth Debug] GITHUB_CLIENT_ID exists:", !!process.env.GITHUB_CLIENT_ID);
console.log("[Auth Debug] GITHUB_CLIENT_SECRET exists:", !!process.env.GITHUB_CLIENT_SECRET);
console.log("[Auth Debug] BETTER_AUTH_SECRET exists:", !!process.env.BETTER_AUTH_SECRET);

export const auth = betterAuth({
  // Use built-in PostgreSQL adapter - pass Pool directly
  // Better Auth will create tables automatically if they don't exist
  database: new Pool({
    connectionString: databaseUrl,
  }),
  
  // Base URL for callbacks
  baseURL: process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  
  // Trusted origins for CORS
  trustedOrigins: [
    "http://localhost:3000",
    process.env.NEXT_PUBLIC_APP_URL || "",
  ].filter(Boolean),
  
  // Email/password auth disabled (only using GitHub)
  emailAndPassword: {
    enabled: false,
  },
  
  // GitHub OAuth
  socialProviders: {
    github: {
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
      // Request repo scope to access user's repositories
      scope: ["read:user", "user:email", "repo"],
    },
  },
  
  // Session configuration
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // 1 day
  },
  
  // Debug logging for development
  logger: {
    disabled: false,
    level: "debug",
  },
});

export type Session = typeof auth.$Infer.Session;
