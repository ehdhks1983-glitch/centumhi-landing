import { Router } from 'express';
import { getSupabase } from '../supabase/client.js';

const router = Router();

// GET /api/usage
router.get('/', async (req, res) => {
  const supabase = getSupabase();
  if (!supabase) return res.json({ total_generations: 0, total_tokens: 0, this_month: 0 });

  const now = new Date();
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();

  const [allLogs, monthLogs, genCount] = await Promise.all([
    supabase.from('usage_logs').select('token_used'),
    supabase.from('usage_logs').select('token_used').gte('created_at', monthStart),
    supabase.from('generations').select('id', { count: 'exact', head: true }),
  ]);

  const totalTokens = (allLogs.data || []).reduce((s, r) => s + (r.token_used || 0), 0);
  const monthTokens = (monthLogs.data || []).reduce((s, r) => s + (r.token_used || 0), 0);

  res.json({
    total_generations: genCount.count || 0,
    total_tokens: totalTokens,
    this_month_tokens: monthTokens,
  });
});

export default router;
