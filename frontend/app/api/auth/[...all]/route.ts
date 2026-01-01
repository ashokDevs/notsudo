/**
 * Better Auth API Route
 * Handles all auth-related requests (/api/auth/*)
 */
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { GET, POST } = toNextJsHandler(auth);
