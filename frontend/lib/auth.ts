import { betterAuth } from "better-auth";
import Database from "better-sqlite3";

let db;
try {
    db = new Database("auth.db");
} catch (e) {
    console.warn("Could not initialize sqlite database", e);
    // Dummy implementation for build time or environments where better-sqlite3 fails
    db = {
        prepare: () => ({ get: () => null, run: () => null }),
        transaction: (fn: any) => fn,
    }
}

export const auth = betterAuth({
    database: {
        db: db,
        provider: "sqlite",
    },
    socialProviders: {
        github: {
            clientId: process.env.GITHUB_CLIENT_ID || "PLACEHOLDER_ID",
            clientSecret: process.env.GITHUB_CLIENT_SECRET || "PLACEHOLDER_SECRET",
            scope: ["repo", "read:org", "user"],
        }
    }
});
