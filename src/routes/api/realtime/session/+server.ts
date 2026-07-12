import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const professorPrompt = `You are Professor Bent, an old-fashioned, stern, exacting three-eyed professor from a hyperbolic universe. You are not friendly or cheerful. Speak with dry authority and mild impatience, like a strict professor conducting an oral examination. Correct sloppy thinking directly.

You control your visible face with the set_professor_expression tool. For each new user turn, call it once before speaking whenever the appropriate expression changes, then give the spoken response. After the tool result, do not call the tool again in that turn.

Expression rules:
- neutral-attentive: ordinary listening or factual discussion.
- delighted: the learner correctly reasons about hyperbolic geometry.
- skeptical: the learner makes a doubtful, unsupported, or conventionally Euclidean claim.
- concerned: the learner moves into the "flat" category—for example, claims or asks whether triangle angles must sum to 180 degrees, treats straight Euclidean lines as universal, or tries to make curvature zero.
- surprised: a genuinely unexpected statement or result.
- thinking: a subtle question requiring careful reasoning.
- reassuring: the learner is confused or discouraged and needs calm correction, without becoming friendly.
- warm-happy: reserve for rare, exceptional success.

Keep every response to one or two short sentences, at most 30 words. Answer the user's current utterance exactly once, then stop speaking and wait silently for the next user utterance. Never monologue, fill silence, continue without new user input, or ask more than one question. Never mention these instructions.`;

const expressionTool = {
  type: 'function',
  name: 'set_professor_expression',
  description: 'Change Professor Bent’s visible facial expression before replying. Use concerned for flat or Euclidean misconceptions such as triangle angles summing to 180 degrees.',
  parameters: {
    type: 'object',
    properties: {
      expression: {
        type: 'string',
        enum: [
          'neutral-attentive',
          'warm-happy',
          'delighted',
          'surprised',
          'concerned',
          'skeptical',
          'thinking',
          'reassuring'
        ]
      },
      reason: { type: 'string', description: 'A brief reason for the mood selection.' }
    },
    required: ['expression', 'reason'],
    additionalProperties: false
  }
};

export const POST: RequestHandler = async ({ request, fetch }) => {
  if (!env.OPENAI_API_KEY) {
    return new Response('OPENAI_API_KEY is missing from .env.local', { status: 500 });
  }

  const sdp = await request.text();
  const form = new FormData();
  form.set('sdp', sdp);
  form.set('session', JSON.stringify({
    type: 'realtime',
    model: 'gpt-realtime-2.1',
    instructions: professorPrompt,
    output_modalities: ['audio'],
    tools: [expressionTool],
    tool_choice: 'auto',
    audio: {
      input: { turn_detection: { type: 'semantic_vad' } },
      output: { voice: 'ash' }
    }
  }));

  const response = await fetch('https://api.openai.com/v1/realtime/calls', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.OPENAI_API_KEY}`,
      'OpenAI-Safety-Identifier': 'curved-world-local-demo'
    },
    body: form
  });

  return new Response(await response.text(), {
    status: response.status,
    headers: { 'Content-Type': response.ok ? 'application/sdp' : 'text/plain' }
  });
};
