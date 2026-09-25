// Keep the utterance alive until completion; ignore callbacks from canceled reads.
export function createStepReader(host, onState, onError) {
  const synth = host.speechSynthesis;
  const supported = Boolean(synth && host.SpeechSynthesisUtterance);
  let active = null;
  let enabled = false;
  function stop() {
    const wasActive = Boolean(active);
    active = null;
    enabled = false;
    if (supported && wasActive) synth.cancel();
    onState(false);
  }
  function toggle(text, step) {
    if (enabled) { stop(); return; }
    read(text, step);
  }
  function next(text, step) {
    if (enabled) read(text, step);
  }
  function read(text, step) {
    if (!supported || !text?.trim()) return;
    try {
      active = null;
      synth.cancel();
      const utterance = new host.SpeechSynthesisUtterance(`Step ${step}. ${text}`);
      const english = synth.getVoices().filter(voice => /^en(?:-|_)/i.test(voice.lang));
      const locale = host.navigator?.language || 'en-IN';
      const voice = english.find(v => v.lang.toLowerCase()===locale.toLowerCase() && /natural|enhanced|premium/i.test(v.name))
        || english.find(v => v.lang.toLowerCase()===locale.toLowerCase())
        || english.find(v => v.default) || english[0];
      if (voice) utterance.voice = voice;
      utterance.lang = voice?.lang || 'en-IN';
      // A measured pace, normal pitch, and sentence punctuation preserve natural prosody.
      utterance.rate = 0.9;
      utterance.pitch = 1;
      utterance.volume = 1;
      active = utterance;
      enabled = true;
      utterance.onend = () => { if (active===utterance) active=null; };
      utterance.onerror = event => {
        if (active!==utterance) return;
        active=null;
        enabled=false;
        onState(false);
        if (!['canceled','interrupted'].includes(event.error)) onError();
      };
      onState(true);
      synth.speak(utterance);
    } catch { active=null; enabled=false; onState(false); onError(); }
  }
  return {supported, toggle, next, stop};
}
