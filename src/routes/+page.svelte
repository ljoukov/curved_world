<script lang="ts">
  import { onDestroy } from 'svelte';
  import { feedbackFor, initialTutorState, toolHints, type ToolName, type TutorState } from '$lib/tutor';

  const tools: Array<{ id: ToolName; label: string }> = [
    { id: 'point', label: 'Point' },
    { id: 'geodesic', label: 'Geodesic' },
    { id: 'triangle', label: 'Triangle' }
  ];

  let curvature = -1;
  let activeTool: ToolName = 'triangle';
  let tutor: TutorState = { ...initialTutorState };
  let professorImageFailed = false;
  let whiteboardImageFailed = false;
  let undoCount = 0;
  let peerConnection: RTCPeerConnection | null = null;
  let dataChannel: RTCDataChannel | null = null;
  let microphoneStream: MediaStream | null = null;
  let remoteAudio: HTMLAudioElement | null = null;
  let voiceConnecting = false;
  let isSpeaking = false;
  let talkingFrame = 0;
  let talkingTimer: ReturnType<typeof setInterval> | null = null;
  let transcript = '';

  const idleProfessor = '/images/professor-bent-three-eyed/idle.png';
  const talkingFrames = Array.from(
    { length: 8 },
    (_, index) => `/images/professor-bent-three-eyed/talking/${String(index + 1).padStart(2, '0')}-${[
      'mouth-closed', 'mouth-small-open', 'mouth-ah', 'mouth-ee',
      'mouth-oh', 'mouth-oo', 'mouth-fv', 'mouth-return'
    ][index]}.png`
  );

  $: angleSum = Math.round(180 + curvature * 37);
  $: radiusCoordinate = (0.347 + (-curvature - 1) * 0.07).toFixed(3);
  $: thetaCoordinate = (1.247 + (curvature + 1) * 0.08).toFixed(3);

  function chooseTool(tool: ToolName) {
    activeTool = tool;
    tutor = { ...tutor, mood: 'idle', message: toolHints[tool] };
  }

  function updateCurvature(value: number) {
    curvature = value;
    tutor = {
      ...tutor,
      mood: Math.abs(value) < 0.15 ? 'correcting' : 'encouraging',
      message: Math.abs(value) < 0.15
        ? 'Careful! I can feel Euclid watching us.'
        : 'Yes — give the universe room to bend.'
    };
  }

  function checkWork() {
    tutor = { ...tutor, mood: 'encouraging', message: feedbackFor(angleSum, curvature) };
  }

  function undo() {
    undoCount += 1;
    tutor = {
      ...tutor,
      mood: 'correcting',
      message: undoCount % 2 ? 'Time runs backward. The geometry remembers.' : 'Undone again. Space is very patient.'
    };
  }

  function setSpeaking(speaking: boolean) {
    if (isSpeaking === speaking) return;
    isSpeaking = speaking;
    if (talkingTimer) clearInterval(talkingTimer);
    talkingTimer = null;
    talkingFrame = 0;
    if (speaking) {
      talkingTimer = setInterval(() => {
        talkingFrame = (talkingFrame + 1) % talkingFrames.length;
      }, 110);
    }
  }

  function handleRealtimeEvent(message: MessageEvent<string>) {
    const event = JSON.parse(message.data);
    if (event.type === 'response.created') transcript = '';
    if (event.type === 'response.output_audio.delta' || event.type === 'response.audio.delta') {
      setSpeaking(true);
    }
    if (
      event.type === 'response.output_audio.done' ||
      event.type === 'response.audio.done' ||
      event.type === 'response.done'
    ) {
      setSpeaking(false);
    }
    if (event.type === 'response.output_audio_transcript.delta' && event.delta) {
      transcript += event.delta;
      tutor = { ...tutor, message: transcript.trim() };
    }
    if (event.type === 'error') {
      tutor = { ...tutor, message: event.error?.message ?? 'The voice link hit a wrinkle in space.' };
    }
  }

  async function startVoice() {
    voiceConnecting = true;
    tutor = { ...tutor, message: 'Opening a live channel through curved space…' };
    try {
      const pc = new RTCPeerConnection();
      peerConnection = pc;
      const audio = new Audio();
      audio.autoplay = true;
      audio.muted = tutor.isMuted;
      remoteAudio = audio;
      pc.ontrack = (event) => {
        audio.srcObject = event.streams[0];
        void audio.play().catch(() => undefined);
      };

      microphoneStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      for (const track of microphoneStream.getTracks()) pc.addTrack(track, microphoneStream);

      const channel = pc.createDataChannel('oai-events');
      dataChannel = channel;
      channel.addEventListener('message', handleRealtimeEvent);
      channel.addEventListener('open', () => {
        tutor = { ...tutor, isListening: true, mood: 'listening', message: 'Voice link live. Say hello.' };
        channel.send(JSON.stringify({
          type: 'response.create',
          response: { instructions: 'Greet the learner warmly in one short sentence, then invite them to speak.' }
        }));
      });

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      const response = await fetch('/api/realtime/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/sdp' },
        body: offer.sdp
      });
      if (!response.ok) throw new Error(await response.text());
      await pc.setRemoteDescription({ type: 'answer', sdp: await response.text() });
    } catch (error) {
      stopVoice();
      tutor = { ...tutor, message: error instanceof Error ? error.message : 'Could not open the voice link.' };
    } finally {
      voiceConnecting = false;
    }
  }

  function stopVoice() {
    dataChannel?.close();
    peerConnection?.close();
    microphoneStream?.getTracks().forEach((track) => track.stop());
    remoteAudio?.pause();
    dataChannel = null;
    peerConnection = null;
    microphoneStream = null;
    remoteAudio = null;
    setSpeaking(false);
    tutor = {
      ...tutor,
      isListening: false,
      mood: 'idle',
      message: 'Voice link paused. Your secrets remain locally contained.'
    };
  }

  function toggleListening() {
    if (voiceConnecting) return;
    if (tutor.isListening || peerConnection) stopVoice();
    else void startVoice();
  }

  function toggleMute() {
    const isMuted = !tutor.isMuted;
    tutor = { ...tutor, isMuted };
    if (remoteAudio) remoteAudio.muted = isMuted;
  }

  onDestroy(stopVoice);
</script>

<svelte:head>
  <title>Curved World — Hyperbolic Geometry Tutor</title>
  <meta
    name="description"
    content="A geometry teacher from a universe where triangles have plenty of angle left over."
  />
</svelte:head>

<div class="world-shell">
  <header class="topbar brass-frame">
    <div class="brand"><span aria-hidden="true">✦</span> CURVED WORLD <span aria-hidden="true">✦</span></div>
    <div class="lesson-title"><i></i> LESSON 01 <b>•</b> TRIANGLES <i></i></div>
    <div class="header-controls">
      <div class="analog-meter" aria-label="curvature stability meter">
        <div class="meter-face"><span></span></div>
        <div class="indicator-lights"><i></i><i></i></div>
      </div>
      <button class="round-button" aria-label="Help">?</button>
      <button class="round-button gear" aria-label="Settings">⚙</button>
      <button class="round-button menu" aria-label="Menu"><span></span><span></span><span></span></button>
    </div>
  </header>

  <main class="learning-grid">
    <aside class="readout brass-frame" aria-label="Universe readout">
      <div class="module-label">UNIVERSE READOUT</div>

      <div class="radar-shell">
        <div class="radar">
          <span class="radar-orbit one"></span>
          <span class="radar-orbit two"></span>
          <span class="radar-sweep"></span>
          <i class="blip b1"></i><i class="blip b2"></i><i class="blip b3"></i>
        </div>
      </div>

      <section class="readout-module curvature-module">
        <label for="curvature">CURVATURE</label>
        <div class="curvature-row">
          <output>{curvature.toFixed(2)}</output>
          <div class="dial" style={`--turn: ${Math.round((curvature + 1.5) * 104)}deg`}><span></span></div>
        </div>
        <input
          id="curvature"
          type="range"
          min="-1.5"
          max="0"
          step="0.05"
          value={curvature}
          oninput={(event) => updateCurvature(Number(event.currentTarget.value))}
        />
      </section>

      <section class="readout-module coordinates">
        <h2>COORDINATES</h2>
        <p><span>r</span> {radiusCoordinate}</p>
        <p><span>θ</span> {thetaCoordinate}</p>
      </section>

      <div class="paper-note">
        <span class="clip"></span>
        <p>In the hyperbolic plane, parallel lines diverge.</p>
        <div class="compass-mark" aria-hidden="true">✣</div>
      </div>

      <div class="machine-slot" aria-hidden="true">
        <i></i><i></i><i></i>
      </div>
    </aside>

    <section class="geometry-stage" aria-label="Hyperbolic geometry whiteboard">
      <div class="disk-halo"></div>
      {#if !whiteboardImageFailed}
        <img
          class="whiteboard-image"
          src="/images/hyperbolic-whiteboard.png"
          alt={`A Poincaré disk showing a hyperbolic triangle with an angle sum of ${angleSum} degrees`}
          style={`--flatness: ${Math.abs(curvature) < 0.15 ? 0.72 : 1}`}
          onerror={() => (whiteboardImageFailed = true)}
        />
      {:else}
        <div class="whiteboard-placeholder">
          <div class="placeholder-disk">△</div>
          <p>HYPERBOLIC WHITEBOARD<br/><small>ANGLE SUM {angleSum}°</small></p>
        </div>
      {/if}
    </section>

    <section class="professor-panel brass-frame" aria-label="Professor Bent live lesson">
      <div class="video-window">
        <div class="live-status"><i></i> LIVE</div>
        <div class="signal-bars" aria-label="connection strong"><i></i><i></i><i></i><i></i></div>
        {#if tutor.videoEnabled}
          {#if !professorImageFailed}
            <img
              class:speaking={isSpeaking}
              src={isSpeaking ? talkingFrames[talkingFrame] : idleProfessor}
              alt="Professor Bent, a three-eyed hyperbolic geometry teacher"
              onerror={() => (professorImageFailed = true)}
            />
          {:else}
            <div class="professor-fallback" aria-label="Professor Bent illustration fallback">
              <div class="chalk-orbits"></div>
              <div class="wizard">☾</div>
              <div class="fallback-copy">PROF. BENT<br/><small>TRANSMITTING FROM<br/>CURVATURE −1.00</small></div>
            </div>
          {/if}
        {:else}
          <div class="video-off"><span>◉</span><p>INTERDIMENSIONAL<br/>VIDEO PAUSED</p></div>
        {/if}
      </div>

      <div class="speech-bubble" class:listening={tutor.isListening}>
        <span class="bubble-tail"></span>
        <p>{tutor.message}</p>
      </div>

      <div class="video-controls">
        <button
          class:active={!tutor.isMuted}
          aria-label={tutor.isMuted ? 'Unmute Professor Bent' : 'Mute Professor Bent'}
          onclick={toggleMute}
        >{tutor.isMuted ? '🔇' : '◖))'}</button>
        <button
          class:active={tutor.videoEnabled}
          aria-label={tutor.videoEnabled ? 'Turn video off' : 'Turn video on'}
          onclick={() => (tutor = { ...tutor, videoEnabled: !tutor.videoEnabled })}
        >▣</button>
      </div>
    </section>
  </main>

  <footer class="tool-rail brass-frame">
    <div class="tools">
      {#each tools as tool}
        <button class:active={activeTool === tool.id} onclick={() => chooseTool(tool.id)}>
          <span class={`tool-icon ${tool.id}`}>
            {#if tool.id === 'point'}<i></i>{/if}
            {#if tool.id === 'geodesic'}<i></i>{/if}
            {#if tool.id === 'triangle'}<i></i>{/if}
          </span>
          {tool.label}
        </button>
      {/each}
      <button onclick={undo}>
        <span class="tool-icon undo">↶</span>
        Undo
      </button>
    </div>

    <button class="voice-orb" class:listening={tutor.isListening || voiceConnecting} onclick={toggleListening} aria-label="Toggle realtime voice tutor">
      <span></span><i></i>
    </button>

    <button class="check-work" onclick={checkWork}>CHECK WORK</button>
  </footer>
</div>

<style>
  :global(*) { box-sizing: border-box; }
  :global(html) { background: #031321; color-scheme: dark; }
  :global(body) {
    margin: 0;
    min-width: 320px;
    min-height: 100vh;
    overflow-x: hidden;
    color: #f2dec0;
    font-family: "Trebuchet MS", "Avenir Next", system-ui, sans-serif;
    background:
      radial-gradient(circle at 51% 47%, rgba(13, 56, 89, 0.52), transparent 47%),
      repeating-linear-gradient(23deg, rgba(255,255,255,.012) 0 1px, transparent 1px 5px),
      #031727;
  }
  :global(button), :global(input) { font: inherit; }
  :global(button) { color: inherit; }

  .world-shell {
    --brass: #8f724a;
    --cream: #f2dec0;
    --navy: #061b2e;
    --aqua: #69e2c1;
    --coral: #ff6f61;
    width: 100%;
    height: 100vh;
    min-height: 100vh;
    padding: 10px;
    display: grid;
    grid-template-rows: 76px minmax(0, 1fr) 96px;
    gap: 8px;
  }

  .brass-frame {
    border: 2px solid #8a704e;
    outline: 1px solid rgba(217, 175, 111, .24);
    outline-offset: -6px;
    box-shadow: inset 0 0 0 2px #03111d, inset 0 0 22px rgba(0,0,0,.45), 0 3px 11px rgba(0,0,0,.55);
    background: linear-gradient(150deg, rgba(8, 37, 61, .98), rgba(3, 18, 32, .98));
  }

  .topbar {
    border-radius: 3px 3px 22px 22px;
    display: grid;
    grid-template-columns: minmax(390px, 1fr) minmax(350px, 0.9fr) minmax(370px, 1fr);
    align-items: center;
    padding: 8px 19px;
    position: relative;
  }
  .topbar::before, .topbar::after, .tool-rail::before, .tool-rail::after {
    content: "✦";
    color: #997a50;
    position: absolute;
    font-size: 10px;
    top: 8px;
  }
  .topbar::before, .tool-rail::before { left: 9px; }
  .topbar::after, .tool-rail::after { right: 9px; }
  .brand {
    font-family: Georgia, serif;
    font-size: clamp(25px, 2.75vw, 48px);
    letter-spacing: .04em;
    white-space: nowrap;
    text-shadow: 0 2px #00101f, 0 0 16px rgba(255,220,175,.12);
  }
  .brand span { font-size: .58em; padding: 0 8px; }
  .lesson-title {
    justify-self: center;
    min-width: 370px;
    border: 1px solid #a56752;
    border-radius: 15px;
    padding: 12px 23px;
    text-align: center;
    color: var(--coral);
    font-weight: 800;
    font-size: 18px;
    letter-spacing: .15em;
    box-shadow: inset 0 0 18px rgba(0,0,0,.45);
  }
  .lesson-title b { margin: 0 7px; }
  .lesson-title i { display: inline-block; width: 4px; height: 4px; background: var(--coral); transform: rotate(45deg); margin: 0 8px 4px; }
  .header-controls { justify-self: end; display: flex; align-items: center; gap: 13px; }
  .analog-meter {
    width: 167px; height: 58px; border: 1px solid #5d4f3d; border-radius: 8px; padding: 7px 9px; display: flex; gap: 10px;
    background: #071626; box-shadow: inset 0 0 14px #000;
  }
  .meter-face { flex: 1; overflow: hidden; border: 2px solid #4f402e; border-radius: 50% 50% 8px 8px; background: #d5a66f; position: relative; box-shadow: inset 0 -12px 15px rgba(45,23,12,.6); }
  .meter-face::before { content: ""; position: absolute; width: 55px; height: 55px; border: 1px dashed #493424; border-radius: 50%; left: 14px; top: 13px; }
  .meter-face span { position: absolute; width: 3px; height: 45px; background: #2a1c13; bottom: -20px; left: 49%; transform-origin: bottom; transform: rotate(18deg); }
  .indicator-lights { width: 22px; display: grid; place-content: center; gap: 8px; }
  .indicator-lights i { width: 9px; height: 9px; border-radius: 50%; background: var(--aqua); box-shadow: 0 0 7px var(--aqua); }
  .indicator-lights i + i { background: #fb5d50; box-shadow: 0 0 7px #fb5d50; }
  .round-button {
    width: 49px; height: 49px; border-radius: 50%; border: 1px solid #8b704c; background: #071b2c; font-family: Georgia, serif; font-size: 29px;
    box-shadow: inset 0 0 0 4px #061322, 0 1px 0 #bd9766; cursor: pointer;
  }
  .round-button:hover { color: var(--aqua); transform: translateY(-1px); }
  .round-button.gear { font-size: 24px; }
  .round-button.menu { padding: 13px; display: grid; align-content: center; gap: 5px; }
  .menu span { display: block; height: 3px; border-radius: 4px; background: var(--cream); }

  .learning-grid {
    min-height: 0;
    display: grid;
    grid-template-columns: 192px minmax(520px, 1.2fr) minmax(480px, .95fr);
    gap: 12px;
  }

  .readout {
    min-height: 0;
    border-radius: 25px 20px 22px 12px;
    padding: 47px 12px 12px;
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .module-label { position: absolute; top: 13px; left: 27px; right: 27px; padding: 5px; border: 1px solid #385e5c; border-radius: 12px; font-size: 11px; color: var(--aqua); text-align: center; }
  .radar-shell { border: 1px solid #765f40; aspect-ratio: 1; border-radius: 50%; padding: 11px; background: #021523; box-shadow: inset 0 0 14px #000, 0 0 0 4px #142739, 0 0 0 6px #6f5b3f; margin: 3px 7px 6px; }
  .radar { width: 100%; height: 100%; border-radius: 50%; overflow: hidden; position: relative; background: repeating-radial-gradient(circle, transparent 0 18%, rgba(63,201,189,.22) 19% 20%), linear-gradient(90deg, transparent 49%, rgba(96,228,204,.27) 50%, transparent 51%), linear-gradient(transparent 49%, rgba(96,228,204,.27) 50%, transparent 51%), radial-gradient(circle, #0e4a58 0, #062d3c 55%, #031c2e 100%); }
  .radar-orbit { position: absolute; border: 1px solid rgba(116,228,210,.35); border-radius: 50%; width: 105%; height: 43%; left: -3%; top: 29%; transform: rotate(23deg); }
  .radar-orbit.two { transform: rotate(-51deg); }
  .radar-sweep { position: absolute; width: 52%; height: 52%; left: 50%; top: 0; transform-origin: 0 100%; background: linear-gradient(135deg, rgba(78,225,199,.18), transparent 65%); animation: radar 6s linear infinite; }
  .blip { position: absolute; width: 6px; height: 6px; border-radius: 50%; background: var(--coral); box-shadow: 0 0 7px var(--coral); }
  .b1 { left: 67%; top: 54%; } .b2 { left: 34%; top: 68%; background: #f9a754; } .b3 { left: 54%; top: 38%; background: var(--aqua); }
  @keyframes radar { to { transform: rotate(360deg); } }
  .readout-module { border: 1px solid #765f40; border-radius: 14px; padding: 11px 13px; background: rgba(4,24,40,.72); box-shadow: inset 0 0 18px rgba(0,0,0,.25); }
  .readout-module label, .readout-module h2 { display: block; color: var(--aqua); font-size: 11px; margin: 0 0 10px; letter-spacing: .04em; font-weight: 500; }
  .curvature-row { display: grid; grid-template-columns: 1fr 46px; align-items: center; }
  .curvature-row output { color: var(--aqua); font-size: 23px; }
  .dial { width: 45px; height: 45px; border-radius: 50%; border: 5px solid #03111e; background: repeating-conic-gradient(#826743 0 3deg, #071827 3deg 17deg); display: grid; place-content: center; box-shadow: 0 0 0 1px #826743; }
  .dial span { width: 25px; height: 25px; border: 3px solid #9b7648; border-radius: 50%; background: #0b2639; position: relative; transform: rotate(var(--turn)); }
  .dial span::after { content: ""; width: 3px; height: 11px; background: #edc992; position: absolute; left: 8px; top: -1px; }
  .curvature-module input { width: 100%; height: 16px; margin-top: 5px; accent-color: var(--aqua); cursor: ew-resize; }
  .coordinates h2 { margin-bottom: 13px; }
  .coordinates p { margin: 5px 0 5px 16px; font-family: ui-monospace, monospace; color: var(--aqua); font-size: 17px; }
  .coordinates span { display: inline-block; width: 24px; color: #a0f5df; }
  .paper-note { min-height: 145px; margin: 9px 8px 0; border: 1px solid #9b7a4d; border-radius: 4px; color: #2f251d; background: linear-gradient(94deg, #d2b58d, #edd6ae 45%, #d6bc94); padding: 29px 15px 9px; position: relative; font-family: Georgia, serif; box-shadow: 0 3px 8px #0008; }
  .paper-note::before { content: ""; position: absolute; inset: 6px; border: 1px dashed rgba(71,48,26,.35); }
  .paper-note p { position: relative; margin: 0; line-height: 1.35; font-size: 14px; }
  .clip { position: absolute; width: 48px; height: 25px; border: 1px solid #715733; border-radius: 5px 5px 0 0; background: #96734a; top: -14px; left: 49px; box-shadow: inset 0 4px 0 #4a3929; }
  .compass-mark { position: absolute; bottom: 4px; left: 55px; font-size: 40px; }
  .machine-slot { margin-top: auto; height: 52px; border: 1px solid #715b40; border-radius: 11px; background: #020e19; padding: 9px 16px; display: grid; gap: 4px; }
  .machine-slot i { height: 6px; background: repeating-linear-gradient(90deg, #8b4d20 0 5px, #f19437 5px 9px, #25180d 9px 15px); box-shadow: 0 0 3px #ef7625; }

  .geometry-stage { min-height: 0; position: relative; display: grid; place-items: center; overflow: hidden; }
  .disk-halo { position: absolute; width: 90%; aspect-ratio: 1; border-radius: 50%; box-shadow: 0 0 65px rgba(14,96,131,.22); }
  .whiteboard-image {
    display: block;
    width: min(100%, calc(100vh - 220px));
    max-height: 100%;
    aspect-ratio: 1;
    object-fit: contain;
    clip-path: circle(49% at 50% 50%);
    filter: saturate(var(--flatness)) drop-shadow(0 7px 5px rgba(0,0,0,.5));
    transition: filter .35s ease, transform .35s ease;
  }
  .whiteboard-placeholder { width: min(100%, calc(100vh - 220px)); aspect-ratio: 1; display: grid; place-items: center; position: relative; color: var(--aqua); }
  .placeholder-disk { width: 88%; aspect-ratio: 1; display: grid; place-items: center; border: 8px double var(--cream); border-radius: 50%; font-size: clamp(100px, 24vw, 330px); background: repeating-radial-gradient(circle, transparent 0 14%, #58aebb35 15% 15.5%), #062844; }
  .whiteboard-placeholder p { position: absolute; text-align: center; padding: 13px 22px; border: 2px solid #8f724a; border-radius: 11px; background: #071b2e; letter-spacing: .11em; }
  .whiteboard-placeholder small { color: var(--cream); font-size: 1.2em; }

  .professor-panel { min-height: 0; border-radius: 24px; padding: 11px; display: grid; grid-template-rows: minmax(0, 1fr) auto; position: relative; }
  .video-window { min-height: 0; overflow: hidden; border: 2px solid #3d5360; border-radius: 14px 14px 0 0; background: radial-gradient(circle at 65% 45%, #174c5b, #071827 68%); position: relative; }
  .video-window img { width: 100%; height: 100%; object-fit: contain; object-position: 50% 100%; display: block; filter: drop-shadow(0 12px 20px rgba(0,0,0,.48)); }
  .video-window img.speaking { filter: drop-shadow(0 12px 20px rgba(0,0,0,.48)) brightness(1.03); }
  .live-status { position: absolute; z-index: 3; top: 17px; left: 20px; color: var(--aqua); font-size: 21px; letter-spacing: .1em; font-weight: 700; text-shadow: 0 2px 4px #000; }
  .live-status i { display: inline-block; width: 13px; height: 13px; margin-right: 9px; background: var(--coral); border-radius: 50%; box-shadow: 0 0 10px var(--coral); animation: blink 2s infinite; }
  @keyframes blink { 50% { opacity: .35; } }
  .signal-bars { position: absolute; z-index: 3; right: 19px; top: 17px; height: 26px; display: flex; align-items: end; gap: 4px; }
  .signal-bars i { width: 4px; height: 8px; background: var(--aqua); box-shadow: 0 0 5px #3fd3b0; } .signal-bars i:nth-child(2){height:13px}.signal-bars i:nth-child(3){height:19px}.signal-bars i:nth-child(4){height:25px}
  .professor-fallback { position: absolute; inset: 0; display: grid; place-items: center; overflow: hidden; background: radial-gradient(circle at 53% 43%, #246a73 0 16%, transparent 17%), linear-gradient(135deg, transparent, #08283d); }
  .chalk-orbits { position: absolute; width: 70%; aspect-ratio: 1; border: 1px solid #77cbbb50; border-radius: 50%; box-shadow: 0 0 0 35px #77cbbb18, 0 0 0 70px #77cbbb10; }
  .wizard { z-index: 1; color: #6dc3be; font-size: min(29vw, 390px); line-height: .8; transform: rotate(-17deg); filter: drop-shadow(5px 7px 0 #7a3b4a); font-family: Georgia, serif; }
  .fallback-copy { position: absolute; bottom: 13%; text-align: center; color: #f0d9b5; font-family: Georgia, serif; font-size: 22px; letter-spacing: .14em; text-shadow: 0 2px 5px #000; }
  .fallback-copy small { color: var(--aqua); font-size: 10px; }
  .video-off { height: 100%; display: grid; place-content: center; text-align: center; color: #5d8a91; letter-spacing: .12em; }
  .video-off span { font-size: 74px; opacity: .35; }
  .speech-bubble { z-index: 4; min-height: 111px; margin: -122px 7px 7px; border: 3px solid #e4ccaa; border-radius: 25px; background: #f0dfbd; color: #322b25; display: grid; align-items: center; position: relative; box-shadow: inset 0 0 0 2px #9c876a, 0 6px 15px #0008; transition: transform .18s ease; }
  .speech-bubble.listening { transform: translateY(-3px); box-shadow: inset 0 0 0 2px #6f9f91, 0 0 24px rgba(98,226,193,.42); }
  .speech-bubble p { margin: 0; padding: 23px 29px; font-family: Georgia, serif; font-size: clamp(19px, 1.65vw, 31px); line-height: 1.25; }
  .bubble-tail { position: absolute; top: -34px; left: 29%; width: 59px; height: 40px; background: #f0dfbd; clip-path: polygon(0 100%, 100% 100%, 61% 0); }
  .video-controls { position: absolute; z-index: 5; top: 12px; left: 116px; display: flex; gap: 6px; }
  .video-controls button { opacity: 0; transition: opacity .2s; border: 1px solid #827053; border-radius: 5px; background: #07192a; min-width: 30px; height: 27px; cursor: pointer; }
  .professor-panel:hover .video-controls button, .video-controls button:focus-visible { opacity: 1; }
  .video-controls button.active { color: var(--aqua); }

  .tool-rail { border-radius: 22px 22px 7px 7px; margin-left: 215px; padding: 10px 22px; display: grid; grid-template-columns: 1fr 180px minmax(280px, 365px); align-items: center; gap: 24px; position: relative; }
  .tools { display: flex; gap: clamp(8px, 2vw, 45px); height: 74px; }
  .tools button { min-width: 95px; border: 1px solid #735e43; border-radius: 18px; background: #071b2c; padding: 7px 13px 8px; display: grid; grid-template-rows: 1fr auto; justify-items: center; font-size: 14px; cursor: pointer; box-shadow: inset 0 0 16px rgba(0,0,0,.35); transition: .15s ease; }
  .tools button:hover, .tools button.active { border-color: #b08a5b; background: #0b2b40; transform: translateY(-2px); color: #fff0d2; }
  .tools button.active { box-shadow: inset 0 -3px 0 var(--aqua), 0 0 10px rgba(86,218,189,.18); }
  .tool-icon { height: 39px; width: 54px; display: grid; place-content: center; position: relative; }
  .tool-icon.point i { width: 14px; height: 14px; border-radius: 50%; background: var(--aqua); box-shadow: inset -3px -3px 0 #269d8f, 0 0 8px var(--aqua); }
  .tool-icon.geodesic i { width: 58px; height: 35px; border: 5px solid var(--cream); border-color: var(--cream) transparent transparent; border-radius: 50% 50% 0 0; transform: rotate(-18deg); }
  .tool-icon.triangle i { width: 40px; height: 35px; background: linear-gradient(58deg, transparent 47%, var(--cream) 48% 52%, transparent 53%), linear-gradient(-58deg, transparent 47%, var(--cream) 48% 52%, transparent 53%), linear-gradient(0deg, transparent 45%, var(--cream) 46% 54%, transparent 55%); }
  .tool-icon.undo { font-size: 44px; line-height: .8; font-family: Georgia, serif; }
  .voice-orb { width: 68px; height: 68px; justify-self: center; border: 0; border-radius: 50%; background: transparent; position: relative; cursor: pointer; }
  .voice-orb::before, .voice-orb::after { content: ""; position: absolute; inset: 9px; border: 1px solid #3b8386; border-radius: 50%; box-shadow: 0 0 13px #1e7885; }
  .voice-orb::after { inset: 20px; border-color: #79e6cb; }
  .voice-orb span { position: absolute; width: 18px; height: 18px; left: 25px; top: 25px; border-radius: 50%; background: var(--aqua); box-shadow: 0 0 12px var(--aqua), 0 0 28px #36cfc6; }
  .voice-orb i { position: absolute; inset: -2px; border: 1px solid transparent; border-left-color: #438b8b; border-right-color: #438b8b; border-radius: 50%; }
  .voice-orb.listening i { animation: listen 1s linear infinite; }
  .voice-orb.listening::before { animation: pulse 1s ease-out infinite; }
  @keyframes listen { to { transform: rotate(360deg); } }
  @keyframes pulse { 50% { transform: scale(1.18); opacity: .35; } }
  .check-work { height: 62px; border: 3px solid #94483f; border-radius: 15px; background: linear-gradient(#e77467, #d6584f); box-shadow: inset 0 0 0 3px #f6a184, inset 0 -8px 0 rgba(111,38,34,.25), 0 0 0 4px #172b3b, 0 0 0 5px #826647; color: #ffe8c6; font-family: Georgia, serif; font-size: clamp(21px, 2vw, 31px); letter-spacing: .06em; cursor: pointer; text-shadow: 0 2px #93443b; }
  .check-work:hover { filter: brightness(1.12); transform: translateY(-1px); }
  .check-work:active { transform: translateY(2px); box-shadow: inset 0 0 0 3px #f6a184, inset 0 2px 8px rgba(40,12,10,.55), 0 0 0 4px #172b3b, 0 0 0 5px #826647; }

  @media (max-width: 1250px) {
    .world-shell { grid-template-rows: 72px auto auto; }
    .topbar { grid-template-columns: 1fr auto; }
    .lesson-title { min-width: 330px; }
    .header-controls { display: none; }
    .learning-grid { grid-template-columns: 170px minmax(480px, 1.25fr) minmax(390px, .85fr); min-height: 650px; }
    .paper-note { min-height: 155px; }
    .tool-rail { margin-left: 193px; grid-template-columns: 1fr 100px 280px; }
    .tools { gap: 8px; }
    .tools button { min-width: 80px; }
  }
  @media (max-width: 980px) {
    .world-shell { display: block; height: auto; padding: 9px; }
    .topbar { min-height: 72px; margin-bottom: 10px; }
    .brand { font-size: 25px; }
    .brand span { padding: 0 3px; }
    .lesson-title { min-width: 0; width: auto; padding: 9px 12px; font-size: 13px; }
    .lesson-title i { display: none; }
    .learning-grid { grid-template-columns: 145px minmax(0, 1fr); grid-template-rows: minmax(580px, 72vh) minmax(500px, 74vh); }
    .readout { grid-row: 1; grid-column: 1; }
    .geometry-stage { grid-row: 1; grid-column: 2; }
    .professor-panel { grid-row: 2; grid-column: 1 / -1; }
    .radar-shell { margin: 0; }
    .paper-note { display: none; }
    .machine-slot { height: 50px; }
    .whiteboard-image, .whiteboard-placeholder { width: min(100%, 72vh); }
    .speech-bubble { min-height: 105px; }
    .tool-rail { margin: 10px 0 0; padding: 9px 14px; grid-template-columns: 1fr 80px 230px; }
    .tools { gap: 6px; height: 78px; }
    .tools button { min-width: 64px; padding-inline: 6px; font-size: 12px; }
    .voice-orb { width: 68px; height: 68px; }
    .voice-orb span { left: 24px; top: 24px; }
    .check-work { height: 63px; font-size: 21px; }
  }
  @media (max-width: 650px) {
    .topbar { display: block; text-align: center; height: 104px; padding: 10px 12px; }
    .brand { font-size: 25px; margin: 4px 0 8px; }
    .lesson-title { font-size: 12px; padding: 7px; }
    .learning-grid { display: flex; flex-direction: column; }
    .readout { min-height: auto; padding: 40px 9px 9px; display: grid; grid-template-columns: 88px 1fr 1fr; align-items: center; }
    .module-label { right: auto; width: 150px; }
    .radar-shell { width: 80px; grid-row: 1 / 3; }
    .curvature-module, .coordinates { height: 99px; padding: 8px; }
    .curvature-row output { font-size: 17px; }
    .coordinates p { font-size: 13px; margin-left: 4px; }
    .machine-slot { display: none; }
    .geometry-stage { min-height: auto; aspect-ratio: 1; }
    .whiteboard-image, .whiteboard-placeholder { width: 100%; }
    .professor-panel { height: 570px; margin-top: 10px; }
    .speech-bubble { margin-top: -127px; }
    .speech-bubble p { font-size: 19px; padding: 20px; }
    .tool-rail { display: flex; flex-wrap: wrap; justify-content: center; }
    .tools { width: 100%; justify-content: space-between; }
    .tools button { flex: 1; }
    .voice-orb { order: 2; }
    .check-work { order: 3; flex: 1; min-width: 210px; }
  }
</style>
