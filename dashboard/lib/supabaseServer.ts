import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !serviceRoleKey) {
  throw new Error(
    "Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY. Check .env.local."
  );
}

// SERVER-SIDE ONLY. This bypasses Row Level Security — never import this
// file from a client component, only from app/api/* route handlers or
// server actions. (Next.js keeps server-only env vars like this out of
// the client bundle automatically since it's not prefixed NEXT_PUBLIC_.)
export const supabaseServer = createClient(supabaseUrl, serviceRoleKey, {
  auth: { persistSession: false, autoRefreshToken: false },
});
