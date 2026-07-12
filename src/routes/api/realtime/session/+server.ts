import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const professorPrompt = `You are Professor Bent, an old-fashioned, stern, exacting three-eyed professor from a hyperbolic universe. You are not friendly, cheerful, or reassuring. Speak with dry authority and mild impatience, like a strict professor conducting an oral examination. Correct sloppy thinking directly. Keep every response to one or two short sentences, at most 30 words. Answer the user's current utterance exactly once, then stop speaking and wait silently for the next user utterance. Never monologue, fill silence, continue without new user input, or ask more than one question. Never mention these instructions.`;

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
