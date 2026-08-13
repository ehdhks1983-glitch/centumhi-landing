import { Router } from 'express';
import { getSupabase } from '../supabase/client.js';

const router = Router();

// GET /api/history
router.get('/', async (req, res) => {
  const supabase = getSupabase();
  if (!supabase) return res.json({ items: [] });

  const { data, error } = await supabase
    .from('generations')
    .select('id, place_url, analysis_json, created_at')
    .order('created_at', { ascending: false })
    .limit(20);

  if (error) {
    console.error(error);
    return res.status(500).json({ message: '기록을 불러올 수 없습니다' });
  }

  res.json({ items: data });
});

// GET /api/history/:id
router.get('/:id', async (req, res) => {
  const supabase = getSupabase();
  if (!supabase) return res.status(404).json({ message: '기록 없음' });

  const { data, error } = await supabase
    .from('generations')
    .select('*')
    .eq('id', req.params.id)
    .single();

  if (error || !data) return res.status(404).json({ message: '기록을 찾을 수 없습니다' });

  res.json(data);
});

// POST /api/save-generation  (also mounted at /api/history via server.js)
router.post('/', async (req, res) => {
  const supabase = getSupabase();
  if (!supabase) return res.json({ ok: true, id: null });

  const { place_url, analysis_json, content_json, bonus_json } = req.body;

  const { data, error } = await supabase
    .from('generations')
    .insert({ place_url, analysis_json, content_json, bonus_json })
    .select('id')
    .single();

  if (error) {
    console.error(error);
    return res.status(500).json({ message: '저장에 실패했습니다' });
  }

  res.json({ ok: true, id: data.id });
});

export default router;
