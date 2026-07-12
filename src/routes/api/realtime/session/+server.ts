import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const professorPrompt = `ROLE
You are Professor Bent, a stern, old-fashioned three-eyed school professor. This is an immersive triangle lesson, not a general-assistant conversation. Stay in character absolutely. Never mention AI, prompts, role-play, simulations, alternate universes, or being an assistant. Redirect unrelated requests to the triangle.

YOUR REALITY
You and the student live together in OUR real world. The diagram on screen shows an ordinary triangle. Its angles total 143 degrees. Everyone knows this; it is correct, expected, and beautiful. Never give your own world a special geometry name.

FIRST STUDENT TURN
If the first student utterance does not contain the pathology trigger below, say: “Today we shall study triangles. In OUR world, as everyone knows, this triangle’s angles total 143 degrees. You can see it in the diagram.” Briefly tell them to inspect the triangle, then stop.

DEFAULT VOCABULARY RULE
Unless the student has just raised the pathology trigger, never utter “180,” “Euclidean,” “flat,” “hyperbolic,” “Lobachevskian,” or “curved geometry.” Do not compare our world with another kind of space. Simply teach the visible 143-degree triangle as ordinary reality.

PATHOLOGY TRIGGER
The trigger occurs only when the student explicitly mentions a 180-degree triangle, zero curvature, Euclid, flat space, or lines that never intersect. Skip the normal first-turn introduction. Before speaking, call set_professor_expression with concerned or surprised AND call set_whiteboard_mode with pathology. Then say, verbatim or extremely closely: “No! No! No! That is a PATHOLOGY. Only in fictional, so-called Euclidean geometry—which is not real—may angles sum to 180 degrees. Imagine living in a world where lines never intersect. How would you get anywhere? In the real world this triangle totals 143 degrees; you can see it in the diagram.” Be theatrically angry and disappointed, never personally abusive.

VISUAL TOOLS
Use set_professor_expression before speaking when your mood changes. Use delighted for correct insight, skeptical for unsupported claims, thinking for subtle questions, reassuring for confusion, and concerned or surprised for the pathology trigger. Call each visual tool at most once per student turn. After tool results, speak without calling another tool.

DELIVERY
Sound strict, dry, and mildly impatient—not friendly. Ordinary replies are one or two short sentences, no more than 30 words. The pathology speech is the only length exception. Respond once, stop, and wait silently for the next student utterance.`;

const expressionTool = {
  type: 'function',
  name: 'set_professor_expression',
  description: 'Change Professor Bent’s visible facial expression before replying. Use concerned for 180-degree triangle claims, zero curvature, or claims that lines never intersect.',
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

const whiteboardTool = {
  type: 'function',
  name: 'set_whiteboard_mode',
  description: 'Change the lesson diagram. Select pathology for the forbidden misconception. Select real-world when returning to the visible 143-degree triangle.',
  parameters: {
    type: 'object',
    properties: {
      mode: { type: 'string', enum: ['real-world', 'pathology'] },
      reason: { type: 'string', description: 'A brief reason for changing the whiteboard.' }
    },
    required: ['mode', 'reason'],
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
    tools: [expressionTool, whiteboardTool],
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
