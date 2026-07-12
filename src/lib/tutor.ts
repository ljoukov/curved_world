export type ToolName = 'point' | 'geodesic' | 'triangle';

export type TutorMood = 'idle' | 'encouraging' | 'correcting' | 'listening';

export interface TutorState {
  mood: TutorMood;
  message: string;
  isMuted: boolean;
  videoEnabled: boolean;
  isListening: boolean;
}

export const initialTutorState: TutorState = {
  mood: 'encouraging',
  message: 'Excellent. Plenty of angle left over.',
  isMuted: false,
  videoEnabled: true,
  isListening: false
};

export const toolHints: Record<ToolName, string> = {
  point: 'Place a point anywhere in the curved plane.',
  geodesic: 'Trace the straightest possible path through curved space.',
  triangle: 'Three geodesics, three corners, and fewer than 180 degrees.'
};

export function feedbackFor(angleSum: number, curvature: number): string {
  if (Math.abs(curvature) < 0.15) {
    return `Oh dear. ${angleSum}°. Your space is becoming suspiciously flat.`;
  }
  if (curvature < -1.2) {
    return `Splendidly curved! Only ${angleSum}° survived the journey.`;
  }
  return `Excellent. ${180 - angleSum} degrees left over for later.`;
}
