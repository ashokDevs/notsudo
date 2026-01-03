/**
 * Script to drop old auth tables and recreate them for Better Auth
 * Run with: node --env-file=.env drop-auth-tables.mjs
 */
import pg from "pg";

const { Pool } = pg;

async function dropAuthTables() {
  const databaseUrl = process.env.DATABASE_URL;
  
  if (!databaseUrl) {
    console.error("DATABASE_URL is not set!");
    process.exit(1);
  }
  
  console.log("Connecting to database...");
  const pool = new Pool({ connectionString: databaseUrl });
  
  try {
    console.log("Dropping existing auth tables...");
    
    // Drop in correct order due to foreign key constraints
    await pool.query('DROP TABLE IF EXISTS verification CASCADE');
    console.log("  ✓ Dropped verification table");
    
    await pool.query('DROP TABLE IF EXISTS session CASCADE');
    console.log("  ✓ Dropped session table");
    
    await pool.query('DROP TABLE IF EXISTS account CASCADE');
    console.log("  ✓ Dropped account table");
    
    await pool.query('DROP TABLE IF EXISTS "user" CASCADE');
    console.log("  ✓ Dropped user table");
    
    console.log("\nAll auth tables dropped successfully!");
    console.log("Better Auth will recreate them automatically on first start.");
    
  } catch (error) {
    console.error("Error dropping tables:", error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

dropAuthTables();
