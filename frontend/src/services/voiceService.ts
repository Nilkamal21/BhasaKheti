/**
 * BhashaKheti - Bengali Voice Interaction & Speech Synthesis Service (Phase 8)
 *
 * Implements lightweight browser-native SpeechRecognition (Web Speech API) and
 * SpeechSynthesis (TTS) adapters with Bengali (bn-IN) configuration, clear permission
 * handling, graceful fallbacks, and zero data telemetry.
 */

// Global type declarations for Web Speech API
declare global {
  interface Window {
    SpeechRecognition?: any;
    webkitSpeechRecognition?: any;
  }
}

export type VoiceState = 'idle' | 'listening' | 'processing' | 'error';

export interface SpeechRecognitionStatus {
  isSupported: boolean;
  isOnline: boolean;
  disclaimerBn: string;
}

export interface VoiceCapabilities {
  recognitionSupported: boolean;
  synthesisSupported: boolean;
  hasBengaliVoice: boolean;
  bengaliVoiceName?: string;
  isOnline: boolean;
}

/**
 * Checks browser speech recognition and synthesis support.
 */
export function checkVoiceCapabilities(): VoiceCapabilities {
  const recognitionSupported = typeof window !== 'undefined' && 
    (Boolean(window.SpeechRecognition) || Boolean(window.webkitSpeechRecognition));
  
  const synthesisSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;
  const isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true;

  let hasBengaliVoice = false;
  let bengaliVoiceName: string | undefined = undefined;

  if (synthesisSupported && window.speechSynthesis) {
    const voices = window.speechSynthesis.getVoices();
    const bnVoice = voices.find(
      (v) => v.lang.toLowerCase().startsWith('bn') || v.name.toLowerCase().includes('bengali') || v.name.toLowerCase().includes('bangla')
    );
    if (bnVoice) {
      hasBengaliVoice = true;
      bengaliVoiceName = bnVoice.name;
    }
  }

  return {
    recognitionSupported,
    synthesisSupported,
    hasBengaliVoice,
    bengaliVoiceName,
    isOnline
  };
}

/**
 * Finds the best available Bengali voice for speech synthesis.
 */
export function getBestBengaliVoice(): SpeechSynthesisVoice | null {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return null;

  const voices = window.speechSynthesis.getVoices();
  // 1. Exact bn-IN match
  let voice = voices.find((v) => v.lang === 'bn-IN' || v.lang === 'bn_IN');
  if (voice) return voice;

  // 2. Any Bengali dialect (bn-BD, bn)
  voice = voices.find((v) => v.lang.toLowerCase().startsWith('bn'));
  if (voice) return voice;

  // 3. Name-based match
  voice = voices.find(
    (v) => v.name.toLowerCase().includes('bengali') || v.name.toLowerCase().includes('bangla')
  );
  return voice || null;
}

/**
 * Creates and configures a SpeechRecognition instance for Bengali (bn-IN).
 */
export function createBengaliSpeechRecognizer(callbacks: {
  onStart: () => void;
  onResult: (transcript: string, isFinal: boolean) => void;
  onError: (errorKey: string, errorMessageBn: string) => void;
  onEnd: () => void;
}) {
  if (typeof window === 'undefined') return null;

  const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognitionClass) {
    callbacks.onError(
      'not_supported',
      'আপনার ব্রাউজারে ভয়েস রিকগনিশন (Speech Recognition) সমর্থিত নয়। অনুগ্রহ করে লিখে প্রশ্ন করুন।'
    );
    return null;
  }

  const recognition = new SpeechRecognitionClass();
  recognition.lang = 'bn-IN'; // Bengali (India)
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    callbacks.onStart();
  };

  recognition.onresult = (event: any) => {
    let interimTranscript = '';
    let finalTranscript = '';

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      const trans = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += trans;
      } else {
        interimTranscript += trans;
      }
    }

    const currentText = finalTranscript || interimTranscript;
    callbacks.onResult(currentText, Boolean(finalTranscript));
  };

  recognition.onerror = (event: any) => {
    let messageBn = 'ভয়েস শনাক্তকরণে সমস্যা হয়েছে।';
    const err = event.error;

    if (err === 'not-allowed') {
      messageBn = 'মাইক্রোফোনের অনুমতি দেওয়া হয়নি (Permission Denied)। ব্রাউজার সেটিংসে গিয়ে মাইক্রোফোন ব্যবহারের অনুমতি দিন।';
    } else if (err === 'no-speech') {
      messageBn = 'কোনো কথা শুনতে পাওয়া যায়নি। অনুগ্রহ করে মাইক্রোফোনে পরিষ্কারভাবে বলুন।';
    } else if (err === 'network') {
      messageBn = 'ইন্টারনেট সংযোগ বিচ্ছিন্ন। ব্রাউজার ভয়েস রিকগনিশনের জন্য সক্রিয় ইন্টারনেট সংযোগ প্রয়োজন।';
    } else if (err === 'audio-capture') {
      messageBn = 'মাইক্রোফোন শনাক্ত করা যায়নি। অনুগ্রহ করে আপনার ডিভাইস মাইক্রোফোন পরীক্ষা করুন।';
    }

    callbacks.onError(err, messageBn);
  };

  recognition.onend = () => {
    callbacks.onEnd();
  };

  return recognition;
}

/**
 * Text-To-Speech (TTS) synthesizer that reads Bengali text aloud.
 * Filters out markdown syntax, technical symbols and provides pause/stop controls.
 */
export class BengaliSpeechSynthesizer {
  private currentUtterance: SpeechSynthesisUtterance | null = null;
  private isSpeakingState: boolean = false;

  public speak(
    text: string,
    onStart?: () => void,
    onEnd?: () => void,
    onError?: (msg: string) => void
  ): boolean {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      if (onError) onError('ব্রাউজারে টেক্সট-টু-স্পিচ (TTS) সমর্থিত নয়।');
      return false;
    }

    // Cancel any ongoing speech
    this.stop();

    // Clean markdown stars, hashes, links
    const cleanText = text
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/#{1,6}\s?/g, '')
      .replace(/\[(.*?)\]\(.*?\)/g, '$1')
      .replace(/`{1,3}.*?`{1,3}/g, '')
      .replace(/\n+/g, ' । ')
      .trim();

    if (!cleanText) return false;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = 'bn-IN';
    utterance.rate = 0.95; // Slightly slower, clear conversational pace for farmers
    utterance.pitch = 1.0;

    const bnVoice = getBestBengaliVoice();
    if (bnVoice) {
      utterance.voice = bnVoice;
    }

    utterance.onstart = () => {
      this.isSpeakingState = true;
      if (onStart) onStart();
    };

    utterance.onend = () => {
      this.isSpeakingState = false;
      this.currentUtterance = null;
      if (onEnd) onEnd();
    };

    utterance.onerror = (e) => {
      this.isSpeakingState = false;
      this.currentUtterance = null;
      if (onError) onError(`স্পিচ সিন্থেসিস ত্রুটি: ${e.error || 'অজানা ত্রুটি'}`);
    };

    this.currentUtterance = utterance;
    window.speechSynthesis.speak(utterance);
    return true;
  }

  public stop(): void {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    this.isSpeakingState = false;
    this.currentUtterance = null;
  }

  public isSpeaking(): boolean {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      return window.speechSynthesis.speaking;
    }
    return this.isSpeakingState;
  }

  public getCurrentUtterance(): SpeechSynthesisUtterance | null {
    return this.currentUtterance;
  }
}

export const speechSynthesizer = new BengaliSpeechSynthesizer();
