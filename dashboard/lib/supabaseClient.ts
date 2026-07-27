import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY. Check .env.local (see .env.example)."
  );
}

// Safe to use in client components — access is governed by Row Level
// Security policies on each table, not by keeping this key secret.
export const supabase = createClient(supabaseUrl, supabaseAnonKey);
