import { Router } from 'express';
import OpenAI from 'openai';

const router = Router();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// POST /api/analyze-place
// Lightweight analysis only — returns analysis without full content generation
router.post('/', async (req, res) => {
  const { place_url, page_text } = req.body;

  if (!place_url && !page_text) {
    return res.status(400).json({ message: '플레이스 링크 또는 페이지 정보가 필요합니다' });
  }

  const ANALYSIS_SCHEMA = {
    type: 'json_schema',
    json_schema: {
      name: 'place_analysis',
      strict: true,
      schema: {
        type: 'object',
        additionalProperties: false,
        required: ['business_name','category','region','main_offer','customer_pain','selling_point','today_topic'],
        properties: {
          business_name: { type: 'string' },
          category:      { type: 'string' },
          region:        { type: 'string' },
          main_offer:    { type: 'string' },
          customer_pain: { type: 'string' },
          selling_point: { type: 'string' },
          today_topic:   { type: 'string' },
        },
      },
    },
  };

  const prompt = `네이버 플레이스를 분석해주세요.
URL: ${place_url}
${page_text ? `\n페이지 정보:\n${page_text.substring(0, 2000)}` : ''}

분석 항목: 가게명, 업종, 지역, 주요 서비스, 고객 페인포인트, 셀링포인트, 오늘의 홍보 주제`;

  try {
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-2024-08-06',
      messages: [
        { role: 'system', content: '한국 소상공인 마케팅 전문가. 모든 응답은 한국어로.' },
        { role: 'user',   content: prompt },
      ],
      response_format: ANALYSIS_SCHEMA,
      max_tokens: 512,
      temperature: 0.6,
    });

    const result = JSON.parse(completion.choices[0].message.content);
    res.json(result);

  } catch (err) {
    console.error('Analyze error:', err);
    res.status(500).json({ message: '분석에 실패했습니다' });
  }
});

export default router;
