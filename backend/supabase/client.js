import { createClient } from '@supabase/supabase-js';

let _client = null;

export function getSupabase() {
  if (_client) return _client;

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key) {
    console.warn('Supabase not configured — history/usage will not be persisted');
    return null;
  }

  _client = createClient(url, key, {
    auth: { persistSession: false },
  });

  return _client;
}
