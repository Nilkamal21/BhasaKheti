import { useState, useEffect, useRef } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  RotateCcw,
  Check,
  AlertCircle,
  HelpCircle,
  Sparkles,
  Info
} from 'lucide-react';
import {
  createBengaliSpeechRecognizer,
  speechSynthesizer,
  checkVoiceCapabilities
} from '../services/voiceService';
import type { VoiceCapabilities } from '../services/voiceService';

interface VoiceAssistantProps {
  onQuestionSubmit: (question: string) => void;
  isSubmitting: boolean;
  disabled?: boolean;
  lastAnswerBn?: string | null;
}

export function VoiceAssistant({
  onQuestionSubmit,
  isSubmitting,
  disabled = false,
  lastAnswerBn = null
}: VoiceAssistantProps) {
  const [capabilities, setCapabilities] = useState<VoiceCapabilities>({
    recognitionSupported: true,
    synthesisSupported: true,
    hasBengaliVoice: false,
    isOnline: true
  });

  const [isListening, setIsListening] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<string>('');
  const [interimText, setInterimText] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [showPermissionHelp, setShowPermissionHelp] = useState<boolean>(false);

  const recognizerRef = useRef<any>(null);

  // Initialize and check capabilities on mount
  useEffect(() => {
    const caps = checkVoiceCapabilities();
    setCapabilities(caps);

    // Some browsers populate voices asynchronously
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      const handleVoicesChanged = () => {
        setCapabilities(checkVoiceCapabilities());
      };
      window.speechSynthesis.onvoiceschanged = handleVoicesChanged;
      return () => {
        window.speechSynthesis.onvoiceschanged = null;
        speechSynthesizer.stop();
      };
    }
  }, []);

  // Stop speaking or listening when component unmounts
  useEffect(() => {
    return () => {
      if (recognizerRef.current) {
        try {
          recognizerRef.current.abort();
        } catch {}
      }
      speechSynthesizer.stop();
    };
  }, []);

  // Auto-speak new response if user asked via voice and audio is available
  useEffect(() => {
    // If speaking was active on previous answer, cancel
    speechSynthesizer.stop();
    setIsSpeaking(false);
  }, [lastAnswerBn]);

  const startListening = () => {
    setErrorMessage(null);
    setShowPermissionHelp(false);
    setTranscript('');
    setInterimText('');

    if (!capabilities.recognitionSupported) {
      setErrorMessage(
        'আপনার ব্রাউজারে ভয়েস শনাক্তকরণ সুবিধা নেই। অনুগ্রহ করে ক্রোম (Chrome), এজ (Edge) বা সাফারি (Safari) ব্যবহার করুন।'
      );
      return;
    }

    // Stop TTS if speaking
    speechSynthesizer.stop();
    setIsSpeaking(false);

    try {
      const recognizer = createBengaliSpeechRecognizer({
        onStart: () => {
          setIsListening(true);
        },
        onResult: (text, isFinal) => {
          if (isFinal) {
            setTranscript(text);
            setInterimText('');
          } else {
            setInterimText(text);
          }
        },
        onError: (errKey, errMsgBn) => {
          setIsListening(false);
          setErrorMessage(errMsgBn);
          if (errKey === 'not-allowed') {
            setShowPermissionHelp(true);
          }
        },
        onEnd: () => {
          setIsListening(false);
        }
      });

      if (recognizer) {
        recognizerRef.current = recognizer;
        recognizer.start();
      }
    } catch (err: any) {
      setIsListening(false);
      setErrorMessage('মাইক্রোফোন চালু করতে সমস্যা হয়েছে: ' + (err.message || 'অজানা ত্রুটি'));
    }
  };

  const stopListening = () => {
    if (recognizerRef.current) {
      try {
        recognizerRef.current.stop();
      } catch {}
    }
    setIsListening(false);
  };

  const handleConfirmSubmit = () => {
    const finalQ = (transcript || interimText).trim();
    if (!finalQ) {
      setErrorMessage('কোনো প্রশ্ন শনাক্ত হয়নি। অনুগ্রহ করে মাইকে কথা বলুন বা টাইপ করুন।');
      return;
    }
    onQuestionSubmit(finalQ);
    setTranscript('');
    setInterimText('');
  };

  const handleResetTranscript = () => {
    setTranscript('');
    setInterimText('');
    setErrorMessage(null);
  };

  const toggleSpeakAnswer = () => {
    if (!lastAnswerBn) return;

    if (isSpeaking) {
      speechSynthesizer.stop();
      setIsSpeaking(false);
    } else {
      const started = speechSynthesizer.speak(
        lastAnswerBn,
        () => setIsSpeaking(true),
        () => setIsSpeaking(false),
        (err) => {
          setIsSpeaking(false);
          setErrorMessage(err);
        }
      );
      if (!started && !capabilities.synthesisSupported) {
        setErrorMessage('আপনার ব্রাউজারে টেক্সট-টু-স্পিচ (TTS) সমর্থিত নয়।');
      }
    }
  };

  return (
    <div className="voice-assistant-card" aria-label="বাংলা ভয়েস সহকারী">
      {/* Voice Control Top Bar */}
      <div className="voice-control-bar">
        <div className="voice-indicator-area">
          <button
            type="button"
            onClick={isListening ? stopListening : startListening}
            disabled={disabled || isSubmitting}
            className={`btn-voice-mic ${isListening ? 'mic-listening' : 'mic-idle'}`}
            aria-label={isListening ? 'কথা বলা বন্ধ করুন' : 'বাংলায় বলুন (Voice)'}
            title={isListening ? 'কথা বলা শেষ হলে থামুন' : 'মাইক্রোফোনে বাংলায় প্রশ্ন বলুন'}
          >
            {isListening ? (
              <>
                <MicOff size={24} className="mic-icon animate-pulse text-red-600" />
                <span className="mic-label">থামুন (Listening...)</span>
              </>
            ) : (
              <>
                <Mic size={24} className="mic-icon text-brand-green" />
                <span className="mic-label">বাংলায় বলুন (Voice)</span>
              </>
            )}
          </button>

          <div className="voice-status-meta">
            <span className="voice-status-title">
              {isListening
                ? '👂 শুনছি... আপনার কৃষিকাজের প্রশ্নটি স্পষ্ট করে বলুন'
                : 'মুখে বলে প্রশ্ন করার জন্য মাইক বাটনে ট্যাপ করুন'}
            </span>
            <span className="voice-status-lang">ভাষা: বাংলা (ভারত • bn-IN)</span>
          </div>
        </div>

        {/* Text-to-Speech Control Button if an answer is displayed */}
        {lastAnswerBn && (
          <div className="voice-tts-action-area">
            <button
              type="button"
              onClick={toggleSpeakAnswer}
              className={`btn-voice-tts ${isSpeaking ? 'tts-playing' : ''}`}
              title={isSpeaking ? 'পড়া বন্ধ করুন' : 'পরামর্শটি বাংলায় শুনুন'}
              aria-label={isSpeaking ? 'পড়া বন্ধ করুন' : 'পরামর্শটি বাংলায় শুনুন'}
            >
              {isSpeaking ? (
                <>
                  <VolumeX size={18} className="text-amber-700 animate-bounce" />
                  <span>থামুন</span>
                </>
              ) : (
                <>
                  <Volume2 size={18} className="text-brand-green" />
                  <span>পরামর্শ শুনুন</span>
                </>
              )}
            </button>
            {capabilities.hasBengaliVoice && (
              <span className="voice-badge-bn">বাংলা ভয়েস সক্রিয়</span>
            )}
          </div>
        )}
      </div>

      {/* Realtime Transcription Preview & Confirmation Area */}
      {(transcript || interimText || isListening) && (
        <div className="voice-transcription-box">
          <div className="transcription-header">
            <div className="transcription-title">
              <Sparkles size={16} className="text-brand-green" />
              <span>শনাক্তকৃত প্রশ্ন (Transcription Preview):</span>
            </div>
            {isListening && (
              <span className="transcription-live-indicator">
                <span className="pulse-dot"></span>
                কথা রেকর্ড হচ্ছে...
              </span>
            )}
          </div>

          <div className="transcription-input-wrap">
            <textarea
              value={transcript || interimText}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="আপনার কথা এখানে লিখিত রূপ নেবে। ভুল হলে নিজেই সম্পাদনা করতে পারবেন..."
              rows={2}
              className="transcription-textarea"
              aria-label="শনাক্তকৃত প্রশ্নের লিখিত রূপ"
            />
          </div>

          <div className="transcription-actions-row">
            <button
              type="button"
              onClick={handleConfirmSubmit}
              disabled={isSubmitting || (!transcript.trim() && !interimText.trim())}
              className="btn-confirm-voice-submit"
            >
              <Check size={16} />
              <span>{isSubmitting ? 'উত্তর খোঁজা হচ্ছে...' : 'এই প্রশ্নটি জিজ্ঞাসা করুন'}</span>
            </button>

            <button
              type="button"
              onClick={handleResetTranscript}
              disabled={isSubmitting}
              className="btn-cancel-voice"
            >
              <RotateCcw size={15} />
              <span>মুছুন</span>
            </button>
          </div>
        </div>
      )}

      {/* Error or Permission Denied Message */}
      {errorMessage && (
        <div className="voice-error-banner" role="alert">
          <AlertCircle size={18} className="text-amber-800 flex-shrink-0" />
          <div className="error-text-wrap">
            <p className="error-message-bn">{errorMessage}</p>
            {showPermissionHelp && (
              <div className="permission-help-hint">
                <HelpCircle size={14} />
                <span>
                  ব্রাউজারের অ্যাড্রেস বারের বাম পাশে তালা (Lock) বা সাইট সেটিংস আইকনে ক্লিক করে <strong>Microphone</strong> অনুমতি <strong>Allow</strong> করে পেজটি রিফ্রেশ করুন।
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Privacy, Online & Data Attribution Notice */}
      <div className="voice-privacy-notice">
        <Info size={13} className="text-gray-500 flex-shrink-0" />
        <span>
          <strong>গোপনীয়তা ও নির্ভরযোগ্যতা:</strong> কোনো অডিও ফাইল ভাষাখেতি সার্ভারে সংরক্ষণ করা হয় না। ব্রাউজার ভয়েস রিকগনিশনের জন্য ইন্টারনেটের প্রয়োজন হতে পারে। প্রশ্ন যাচাই করে তবেই জমা দিন।
        </span>
      </div>
    </div>
  );
}
