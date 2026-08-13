import { Router } from 'express';
import OpenAI from 'openai';
import { getSupabase } from '../supabase/client.js';

const router = Router();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// ─── JSON Schema for OpenAI Structured Outputs ────────────
const CONTENT_SCHEMA = {
  type: 'json_schema',
  json_schema: {
    name: 'content_generation',
    strict: true,
    schema: {
      type: 'object',
      additionalProperties: false,
      required: ['analysis', 'contents', 'bonus'],
      properties: {
        analysis: {
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
        contents: {
          type: 'object',
          additionalProperties: false,
          required: ['place_post','blog','instagram','threads','shorts','kakao','card_news'],
          properties: {
            place_post: {
              type: 'object', additionalProperties: false,
              required: ['title','body'],
              properties: { title: { type: 'string' }, body: { type: 'string' } },
            },
            blog: {
              type: 'object', additionalProperties: false,
              required: ['title','body','tags'],
              properties: {
                title: { type: 'string' },
                body:  { type: 'string' },
                tags:  { type: 'array', items: { type: 'string' } },
              },
            },
            instagram: {
              type: 'object', additionalProperties: false,
              required: ['caption','hashtags'],
              properties: {
                caption:  { type: 'string' },
                hashtags: { type: 'array', items: { type: 'string' } },
              },
            },
            threads: {
              type: 'object', additionalProperties: false,
              required: ['posts'],
              properties: { posts: { type: 'array', items: { type: 'string' } } },
            },
            shorts: {
              type: 'object', additionalProperties: false,
              required: ['hook','script','scenes'],
              properties: {
                hook:   { type: 'string' },
                script: { type: 'string' },
                scenes: { type: 'array', items: { type: 'string' } },
              },
            },
            kakao: {
              type: 'object', additionalProperties: false,
              required: ['message'],
              properties: { message: { type: 'string' } },
            },
            card_news: {
              type: 'object', additionalProperties: false,
              required: ['slides'],
              properties: { slides: { type: 'array', items: { type: 'string' } } },
            },
          },
        },
        bonus: {
          type: 'object', additionalProperties: false,
          required: ['title_candidates','hashtags'],
          properties: {
            title_candidates: { type: 'array', items: { type: 'string' } },
            hashtags:         { type: 'array', items: { type: 'string' } },
          },
        },
      },
    },
  },
};

// ─── System prompt ────────────────────────────────────────
const SYSTEM_PROMPT = `당신은 한국 소상공인 전문 마케팅 콘텐츠 AI입니다.
네이버 플레이스 정보를 분석해 오늘 바로 사용할 수 있는 홍보 콘텐츠를 생성합니다.

규칙:
- 모든 콘텐츠는 한국어로 작성
- 실제 업주가 오늘 바로 붙여넣기 해서 올릴 수 있는 완성도
- 플랫폼별 특성에 맞는 톤앤매너 적용
- 과장·허위 내용 금지
- 고객 심리 기반의 구체적인 오늘의 홍보 주제 설정`;

// ─── POST /api/generate ───────────────────────────────────
router.post('/', async (req, res) => {
  const { place_url, page_text, tones = [] } = req.body;

  if (!place_url && !page_text) {
    return res.status(400).json({ message: '플레이스 링크 또는 페이지 정보가 필요합니다' });
  }

  const userPrompt = buildPrompt(place_url, page_text, tones);

  try {
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-2024-08-06',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user',   content: userPrompt },
      ],
      response_format: CONTENT_SCHEMA,
      max_tokens: 4096,
      temperature: 0.8,
    });

    const result = JSON.parse(completion.choices[0].message.content);

    // Fire-and-forget save to Supabase
    saveToSupabase(place_url, result, completion.usage).catch(console.error);

    res.json(result);

  } catch (err) {
    console.error('OpenAI error:', err);
    res.status(500).json({ message: '콘텐츠 생성에 실패했습니다. 잠시 후 다시 시도해주세요.' });
  }
});

// ─── Helpers ──────────────────────────────────────────────
function buildPrompt(url, pageText, tones) {
  const toneMap = {
    friendly:     '더 친근하고 따뜻한 톤으로 작성',
    professional: '더 전문적이고 신뢰감 있는 톤으로 작성',
    reservation:  '예약 유도 CTA를 강조',
    visit:        '방문 유도 내용을 중심으로 작성',
  };

  let prompt = `다음 네이버 플레이스 정보를 분석해 오늘의 홍보 콘텐츠를 생성해주세요.\n\n`;
  prompt += `플레이스 URL: ${url}\n\n`;

  if (pageText?.trim()) {
    prompt += `추출된 페이지 정보:\n${pageText.substring(0, 3000)}\n\n`;
  }

  const activeTones = tones.map(t => toneMap[t]).filter(Boolean);
  if (activeTones.length) {
    prompt += `톤 요구사항:\n${activeTones.map(t => `- ${t}`).join('\n')}\n\n`;
  }

  prompt += `생성 요구사항:
[분석] 가게명, 업종, 지역, 주요 서비스, 고객 페인포인트, 셀링포인트, 오늘의 홍보 주제
[콘텐츠]
  - 플레이스 소식: 제목 + 본문 (200자 내외)
  - 블로그: 제목 + 본문 (600자 이상) + 태그 10개
  - 인스타그램: 캡션 (이모지 포함) + 해시태그 20개
  - 쓰레드: 3-5개 연속 포스트 (각 500자 이내)
  - 쇼츠 15초 대본: 후킹 멘트 + 전체 대본 + 장면 구성 5개
  - 카카오톡 홍보 문구: 단문 (150자 내외)
  - 카드뉴스: 5장 문구 (각 2-3문장)
[보너스] 제목 후보 10개 + 해시태그 20개`;

  return prompt;
}

async function saveToSupabase(placeUrl, result, usage) {
  const supabase = getSupabase();
  if (!supabase) return;

  await supabase.from('generations').insert({
    place_url: placeUrl,
    analysis_json: result.analysis,
    content_json: result.contents,
    bonus_json: result.bonus,
  });

  await supabase.from('usage_logs').insert({
    action: 'generate',
    token_used: usage?.total_tokens || 0,
  });
}

export default router;
