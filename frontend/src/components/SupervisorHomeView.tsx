import React, { useState, useRef, useEffect } from 'react';
import {
  Mic,
  Camera,
  Send,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  ShieldCheck,
  ExternalLink,
  Volume2,
  VolumeX,
  X
} from 'lucide-react';
import { sendSupervisorMessage } from '../services/api';
import type { SupervisorChatResponse, SupervisorTurn } from '../services/api';
import { createBengaliSpeechRecognizer, speechSynthesizer } from '../services/voiceService';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  imagePreview?: string;
  toolsInvoked?: string[];
  followUpPrompt?: string | null;
  citations?: Array<{ id?: string; title_bn?: string; source_org?: string; source_url?: string }>;
  safetyWarnings?: string[];
  llmUsed?: boolean;
}

// 4 Visual Suggestion Cards directly from Reference Image
export const VISUAL_SUGGESTIONS = [
  {
    id: 'paddy_disease',
    labelBn: 'ধানের সমস্যা',
    sublabelBn: 'রোগ ও প্রতিকার',
    query: 'ধানের সমস্যা ও রোগ প্রতিকারের উপায় কী?',
    theme: 'paddy',
    iconType: 'rice'
  },
  {
    id: 'weather_rain',
    labelBn: 'বৃষ্টি ও আবহাওয়া',
    sublabelBn: 'বৃষ্টির পূর্বাভাস ও সেচ',
    query: 'আজ কি বৃষ্টি হবে? বর্তমান আবহাওয়া কেমন?',
    theme: 'weather',
    iconType: 'weather'
  },
  {
    id: 'market_rates',
    labelBn: 'আজকের বাজারদর',
    sublabelBn: 'মান্ডি দর ও যাচাই',
    query: 'আজকের প্রধান ফসলের বাজারদর কত?',
    theme: 'market',
    iconType: 'market'
  },
  {
    id: 'govt_schemes',
    labelBn: 'সরকারি প্রকল্প',
    sublabelBn: 'কৃষক বন্ধু ও অনুদান',
    query: 'পশ্চিমবঙ্গের কৃষকদের জন্য সরকারি প্রকল্পসমূহ কী কী?',
    theme: 'schemes',
    iconType: 'schemes'
  }
];

export function SupervisorHomeView() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState<string>('');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [imageType, setImageType] = useState<string>('auto'); // 'leaf', 'soil', 'auto'
  const [loading, setLoading] = useState<boolean>(false);
  const [speakingMsgId, setSpeakingMsgId] = useState<string | null>(null);

  // Immediate Voice Recognition State
  const [isListening, setIsListening] = useState<boolean>(false);
  const [voiceInterimText, setVoiceInterimText] = useState<string>('');
  const [voiceNotice, setVoiceNotice] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognizerRef = useRef<any>(null);
  const chatScrollEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of conversation
  useEffect(() => {
    chatScrollEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages, loading]);

  // Clean up voice recognizer and audio on unmount
  useEffect(() => {
    return () => {
      if (recognizerRef.current) {
        try {
          recognizerRef.current.abort();
        } catch (_) {}
      }
      speechSynthesizer.stop();
    };
  }, []);

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedImage(file);
      const url = URL.createObjectURL(file);
      setImagePreviewUrl(url);

      // Spoken guidance to assist farmers immediately
      try {
        speechSynthesizer.speak('এই ছবির বিষয়ে আপনার কী সাহায্য বা পরামর্শ দরকার? বলুন বা লিখুন।', () => {});
      } catch (_) {}
    }
  };

  const handleClearImage = () => {
    setSelectedImage(null);
    if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
    setImagePreviewUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    speechSynthesizer.stop();
  };

  const executeSendMessage = async (queryText?: string, imageOverride?: File) => {
    // If voice recognition is running, stop it
    if (isListening && recognizerRef.current) {
      try {
        recognizerRef.current.stop();
      } catch (_) {}
      setIsListening(false);
    }

    const q = (queryText !== undefined ? queryText : inputText).trim();
    const img = imageOverride !== undefined ? imageOverride : selectedImage;

    if (!q && !img) return;

    const userMsgId = 'msg-' + Date.now();
    const newUserMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      text: q || (img ? 'ছবি আপলোড করেছি, অনুগ্রহ করে বিশ্লেষণ করে বলুন।' : ''),
      imagePreview: img && imagePreviewUrl ? imagePreviewUrl : undefined
    };

    setMessages((prev) => [...prev, newUserMsg]);
    setInputText('');
    setVoiceInterimText('');
    setVoiceNotice(null);
    setLoading(true);

    // Build history turns for multi-turn supervisor
    const historyTurns: SupervisorTurn[] = messages.slice(-4).map((m) => ({
      role: m.sender === 'user' ? 'user' : 'assistant',
      content: m.text,
      tools_called: m.toolsInvoked
    }));

    try {
      const res: SupervisorChatResponse = await sendSupervisorMessage(
        q || undefined,
        img || undefined,
        imageType,
        undefined,
        23.23,
        87.86,
        historyTurns
      );

      const assistantMsgId = 'msg-' + (Date.now() + 1);
      const newAssistantMsg: ChatMessage = {
        id: assistantMsgId,
        sender: 'assistant',
        text: res.answer_bn,
        toolsInvoked: res.tools_invoked,
        followUpPrompt: res.follow_up_prompt_bn,
        citations: res.citations,
        safetyWarnings: res.safety_warnings,
        llmUsed: res.llm_used
      };

      setMessages((prev) => [...prev, newAssistantMsg]);
      handleClearImage();

      // Automatically speak the response aloud in Bengali as soon as generated
      if (res.answer_bn) {
        try {
          speechSynthesizer.stop();
          speechSynthesizer.speak(
            res.answer_bn,
            () => setSpeakingMsgId(assistantMsgId),
            () => setSpeakingMsgId(null),
            () => setSpeakingMsgId(null)
          );
        } catch (_) {}
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: 'msg-' + (Date.now() + 1),
        sender: 'assistant',
        text: 'সুপারভাইজার প্রক্রিয়াকরণে ত্রুটি: ' + (err.message || 'অনুগ্রহ করে কিছুক্ষণ পর আবার চেষ্টা করুন।'),
        safetyWarnings: ['নেটওয়ার্ক বা সার্ভার সমস্যাজনিত কারণে উত্তর তৈরি করা যায়নি।']
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  // Immediate Microphone Action
  const toggleVoiceInput = () => {
    setVoiceNotice(null);

    if (isListening) {
      if (recognizerRef.current) {
        try {
          recognizerRef.current.stop();
        } catch (_) {}
      }
      setIsListening(false);
      setVoiceInterimText('');
      return;
    }

    const recognizer = createBengaliSpeechRecognizer({
      onStart: () => {
        setIsListening(true);
        setVoiceNotice('শুনছি... আপনার প্রশ্নটি স্পষ্ট বাংলায় বলুন।');
      },
      onResult: (transcript: string, isFinal: boolean) => {
        setVoiceInterimText(transcript);
        setInputText(transcript);

        if (isFinal && transcript.trim()) {
          setIsListening(false);
          setVoiceNotice(null);
          executeSendMessage(transcript.trim());
        }
      },
      onError: (_key: string, messageBn: string) => {
        setIsListening(false);
        setVoiceNotice(messageBn);
      },
      onEnd: () => {
        setIsListening(false);
      }
    });

    if (recognizer) {
      recognizerRef.current = recognizer;
      try {
        recognizer.start();
      } catch (err) {
        setIsListening(false);
        setVoiceNotice('ভয়েস শনাক্তকরণ শুরু করা যায়নি। অনুগ্রহ করে টাইপ করে প্রশ্ন করুন।');
      }
    } else {
      setVoiceNotice('আপনার ব্রাউজারে সরাসরি ভয়েস শনাক্তকরণ সুবিধা নেই। অনুগ্রহ করে টাইপ করে প্রশ্ন করুন।');
    }
  };

  const toggleSpeakAnswer = (msgId: string, answerText: string) => {
    if (speakingMsgId === msgId) {
      speechSynthesizer.stop();
      setSpeakingMsgId(null);
    } else {
      speechSynthesizer.stop();
      const started = speechSynthesizer.speak(
        answerText,
        () => setSpeakingMsgId(msgId),
        () => setSpeakingMsgId(null),
        () => setSpeakingMsgId(null)
      );
      if (!started) setSpeakingMsgId(null);
    }
  };

  return (
    <div className="unified-conversation-container" aria-label="ভাষাখেতি সুপারভাইজার সহকারী">
      {/* Main Conversation Window */}
      <div className="conversation-card-panel">
        {/* State A: First-time Welcome & 4 Visual Suggestion Cards */}
        {messages.length === 0 ? (
          <div className="welcome-first-state">
            {/* Bengali Greeting Bubble matching Reference Image */}
            <div className="greeting-bubble-row">
              <div className="assistant-avatar-circle" aria-hidden="true">
                {/* Stylized Two Leaves Icon */}
                <svg viewBox="0 0 32 32" className="avatar-leaf-svg" fill="none">
                  <path d="M8 26C8 26 10 16 18 11C26 6 28 3 28 3C28 3 27 11 22 16C17 21 11 24 8 26Z" fill="#1b5e20" />
                  <path d="M10 24C10 24 13 17 19 13C24 9 27 6 27 6C27 6 24 13 19 18C15 21 11 23 10 24Z" fill="#4caf50" />
                  <path d="M8 26C8 26 7 18 3 14C3 14 9 13 14 17" fill="#81c784" />
                </svg>
              </div>
              <div className="greeting-text-box">
                <h2 className="greeting-title">নমস্কার!</h2>
                <p className="greeting-subtext">আপনি কী জানতে চান?</p>
              </div>
            </div>

            {/* 4 Visual Suggestion Cards */}
            <div className="visual-suggestions-grid">
              {VISUAL_SUGGESTIONS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => executeSendMessage(item.query)}
                  className={`suggestion-card card-${item.theme}`}
                  aria-label={`${item.labelBn} (${item.sublabelBn})`}
                >
                  <div className="suggestion-icon-wrap">
                    {item.iconType === 'rice' && (
                      /* Golden Rice / Paddy Sheaf */
                      <svg viewBox="0 0 64 64" className="suggestion-svg" fill="none">
                        <path d="M16 54C16 54 22 34 26 24C30 14 32 8 32 8C32 8 28 22 24 36C20 48 16 54 16 54Z" fill="#2e7d32" />
                        <path d="M18 52C18 52 28 40 38 34C48 28 54 26 54 26C54 26 44 32 34 40C26 46 18 52 18 52Z" fill="#388e3c" />
                        <path d="M18 52C22 42 30 28 44 14" stroke="#f59e0b" strokeWidth="3" strokeLinecap="round" />
                        <ellipse cx="44" cy="14" rx="4" ry="7" transform="rotate(35 44 14)" fill="#fbbf24" />
                        <ellipse cx="40" cy="18" rx="4" ry="6.5" transform="rotate(40 40 18)" fill="#f59e0b" />
                        <ellipse cx="48" cy="18" rx="3.5" ry="6" transform="rotate(25 48 18)" fill="#fcd34d" />
                        <ellipse cx="36" cy="23" rx="4" ry="6" transform="rotate(45 36 23)" fill="#fbbf24" />
                        <ellipse cx="43" cy="25" rx="3.5" ry="6" transform="rotate(30 43 25)" fill="#f59e0b" />
                        <ellipse cx="32" cy="30" rx="3.5" ry="5.5" transform="rotate(50 32 30)" fill="#fcd34d" />
                        <ellipse cx="38" cy="32" rx="3.5" ry="5.5" transform="rotate(35 38 32)" fill="#fbbf24" />
                        <ellipse cx="28" cy="37" rx="3.5" ry="5.5" transform="rotate(55 28 37)" fill="#f59e0b" />
                      </svg>
                    )}

                    {item.iconType === 'weather' && (
                      /* Rain Cloud with Sun */
                      <svg viewBox="0 0 64 64" className="suggestion-svg" fill="none">
                        <circle cx="42" cy="22" r="11" fill="#f59e0b" />
                        <path d="M42 6V10M42 34V38M26 22H30M54 22H58M31 11L34 14M50 30L53 33M31 33L34 30M50 14L53 11" stroke="#f59e0b" strokeWidth="2.5" strokeLinecap="round" />
                        <path d="M18 42C14.6863 42 12 39.3137 12 36C12 32.9624 14.2582 30.4518 17.2289 30.0573C17.0783 29.3957 17 28.7076 17 28C17 22.4772 21.4772 18 27 18C31.5791 18 35.4206 21.0827 36.5746 25.2974C37.6094 24.4844 38.9056 24 40.3125 24C43.4536 24 46 26.5464 46 29.6875C46 30.229 45.9242 30.7528 45.7828 31.2504C48.1969 32.1818 49.914 34.5422 49.914 37.314C49.914 40.8524 47.0454 43.721 43.507 43.721H18C16.8954 43.721 16 42.8256 16 41.721V41.721" fill="#38bdf8" />
                        <path d="M22 46L19 54" stroke="#0284c7" strokeWidth="2.5" strokeLinecap="round" />
                        <path d="M29 46L26 55" stroke="#0284c7" strokeWidth="2.5" strokeLinecap="round" />
                        <path d="M36 46L33 54" stroke="#0284c7" strokeWidth="2.5" strokeLinecap="round" />
                        <path d="M43 46L40 53" stroke="#0284c7" strokeWidth="2.5" strokeLinecap="round" />
                      </svg>
                    )}

                    {item.iconType === 'market' && (
                      /* Rupee Money Sack */
                      <svg viewBox="0 0 64 64" className="suggestion-svg" fill="none">
                        <path d="M24 22C24 22 14 26 14 42C14 52 22 55 32 55C42 55 50 52 50 42C50 26 40 22 40 22" fill="#d97706" />
                        <path d="M25 24C25 24 16 28 16 42C16 50 23 53 32 53C41 53 48 50 48 42C48 28 39 24 39 24" fill="#f59e0b" />
                        <path d="M24 22C24 22 22 16 26 13C30 10 34 10 38 13C42 16 40 22 40 22" fill="#d97706" />
                        <rect x="23" y="21" width="18" height="4" rx="2" fill="#92400e" />
                        <text x="32" y="42" textAnchor="middle" fill="#78350f" fontSize="18" fontWeight="bold" fontFamily="sans-serif">₹</text>
                        <ellipse cx="20" cy="53" rx="6" ry="3" fill="#fcd34d" stroke="#d97706" strokeWidth="1.2" />
                        <ellipse cx="44" cy="53" rx="6" ry="3" fill="#fcd34d" stroke="#d97706" strokeWidth="1.2" />
                        <ellipse cx="49" cy="51" rx="5" ry="2.5" fill="#f59e0b" stroke="#b45309" strokeWidth="1" />
                        <ellipse cx="15" cy="51" rx="5" ry="2.5" fill="#f59e0b" stroke="#b45309" strokeWidth="1" />
                      </svg>
                    )}

                    {item.iconType === 'schemes' && (
                      /* Government Building */
                      <svg viewBox="0 0 64 64" className="suggestion-svg" fill="none">
                        <path d="M24 24C24 16 27 12 32 12C37 12 40 16 40 24Z" fill="#a78bfa" />
                        <path d="M26 24C26 18 28 14 32 14C36 14 38 18 38 24Z" fill="#c4b5fd" />
                        <path d="M32 12V6" stroke="#4c1d95" strokeWidth="1.5" />
                        <path d="M32 6L40 9L32 12Z" fill="#ef4444" />
                        <polygon points="12,28 32,18 52,28" fill="#8b5cf6" />
                        <polygon points="15,27 32,19.5 49,27" fill="#a78bfa" />
                        <rect x="15" y="28" width="34" height="19" fill="#ede9fe" />
                        <rect x="18" y="29" width="4" height="17" fill="#7c3aed" />
                        <rect x="25" y="29" width="4" height="17" fill="#7c3aed" />
                        <rect x="35" y="29" width="4" height="17" fill="#7c3aed" />
                        <rect x="42" y="29" width="4" height="17" fill="#7c3aed" />
                        <path d="M30 46V36C30 34.5 31 33.5 32 33.5C33 33.5 34 34.5 34 36V46" fill="#4c1d95" />
                        <rect x="10" y="47" width="44" height="3" rx="1.5" fill="#7c3aed" />
                        <rect x="8" y="50" width="48" height="4" rx="2" fill="#6d28d9" />
                      </svg>
                    )}
                  </div>
                  <span className="suggestion-label-bn">{item.labelBn}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* State B: Active Multi-Turn Conversation Stream */
          <div className="active-chat-stream">
            {messages.map((m) => {
              const isUser = m.sender === 'user';
              return (
                <div key={m.id} className={`stream-row ${isUser ? 'user-stream-row' : 'assistant-stream-row'}`}>
                  {!isUser && (
                    <div className="assistant-stream-avatar" aria-hidden="true">
                      <svg viewBox="0 0 32 32" className="avatar-mini-leaf" fill="none">
                        <path d="M8 26C8 26 10 16 18 11C26 6 28 3 28 3C28 3 27 11 22 16C17 21 11 24 8 26Z" fill="#1b5e20" />
                        <path d="M10 24C10 24 13 17 19 13C24 9 27 6 27 6C27 6 24 13 19 18C15 21 11 23 10 24Z" fill="#4caf50" />
                      </svg>
                    </div>
                  )}

                  <div className={`stream-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
                    {/* User Attached Photo Thumbnail */}
                    {m.imagePreview && (
                      <div className="stream-image-wrap">
                        <img src={m.imagePreview} alt="আপলোড করা ছবি" className="stream-photo-preview" />
                      </div>
                    )}

                    {/* Main Text Content */}
                    <div className="stream-text-content">
                      {m.text.split('\n').map((line, lIdx) => (
                        <p key={lIdx} className={line.startsWith('**') ? 'text-bold-emphasis' : 'text-regular-line'}>
                          {line.replace(/\*\*/g, '')}
                        </p>
                      ))}
                    </div>

                    {/* Verified Grounded Citations */}
                    {!isUser && m.citations && m.citations.length > 0 && (
                      <div className="stream-citations-bar">
                        <div className="citation-tag-title">
                          <ShieldCheck size={14} className="text-emerald-700" />
                          <span>যাচাইকৃত উৎস:</span>
                        </div>
                        <div className="citation-pills-list">
                          {m.citations.map((c, cIdx) => (
                            <a
                              key={cIdx}
                              href={c.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="citation-link-badge"
                            >
                              <span>{c.source_org}</span>
                              <ExternalLink size={10} />
                            </a>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Safety Warnings if applicable */}
                    {!isUser && m.safetyWarnings && m.safetyWarnings.length > 0 && (
                      <div className="stream-safety-notice">
                        {m.safetyWarnings.map((w, wIdx) => (
                          <div key={wIdx} className="safety-notice-line">
                            <AlertTriangle size={14} className="text-amber-800 flex-shrink-0" />
                            <span>{w}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Interactive Follow-up Question Chip */}
                    {!isUser && m.followUpPrompt && (
                      <div className="stream-followup-box">
                        <Sparkles size={14} className="text-amber-700 flex-shrink-0" />
                        <span className="followup-text">{m.followUpPrompt}</span>
                      </div>
                    )}

                    {/* Bengali Text-to-Speech Playback Button */}
                    {!isUser && (
                      <div className="stream-tts-bar">
                        <button
                          type="button"
                          onClick={() => toggleSpeakAnswer(m.id, m.text)}
                          className={`btn-stream-speak ${speakingMsgId === m.id ? 'speak-active' : ''}`}
                          title={speakingMsgId === m.id ? 'পড়া থামান' : 'পরামর্শ বাংলায় শুনুন'}
                          aria-label={speakingMsgId === m.id ? 'পড়া থামান' : 'পরামর্শ শুনুন'}
                        >
                          {speakingMsgId === m.id ? (
                            <>
                              <VolumeX size={16} />
                              <span>থামুন</span>
                            </>
                          ) : (
                            <>
                              <Volume2 size={16} />
                              <span>পরামর্শ শুনুন</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* In-Flight Thinking / Processing Indicator */}
            {loading && (
              <div className="stream-row assistant-stream-row">
                <div className="assistant-stream-avatar" aria-hidden="true">
                  <RefreshCw size={18} className="animate-spin text-emerald-700" />
                </div>
                <div className="stream-bubble assistant-bubble loading-bubble">
                  <RefreshCw size={16} className="animate-spin text-emerald-600" />
                  <span>তথ্য ও মডেল যাচাই করে উত্তর তৈরি হচ্ছে...</span>
                </div>
              </div>
            )}

            <div ref={chatScrollEndRef} />
          </div>
        )}
      </div>

      {/* Live Voice Status Feedback */}
      {voiceNotice && (
        <div className="voice-status-banner" role="status">
          <span className="voice-status-dot animate-ping" />
          <span>{voiceNotice}</span>
          <button type="button" onClick={() => setVoiceNotice(null)} className="btn-close-notice">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Selected Image Thumbnail Badge above Input Bar */}
      {imagePreviewUrl && (
        <div className="image-attachment-chip">
          <div className="attachment-left">
            <img src={imagePreviewUrl} alt="নির্বাচিত ছবি" className="attachment-thumb" />
            <div className="attachment-info">
              <div className="attachment-voice-prompt">
                <span className="attachment-title">📷 নির্বাচিত ছবি প্রস্তুত: এই ছবির বিষয়ে আপনার কী সাহায্য বা পরামর্শ দরকার?</span>
                <span className="attachment-subprompt">নিচের মাইকে ট্যাপ করে কথা বলুন বা লিখে পাঠান</span>
              </div>
              <div className="attachment-type-options">
                <button
                  type="button"
                  onClick={() => setImageType('leaf')}
                  className={`chip-type-tag ${imageType === 'leaf' ? 'active' : ''}`}
                >
                  আক্রান্ত পাতা
                </button>
                <button
                  type="button"
                  onClick={() => setImageType('soil')}
                  className={`chip-type-tag ${imageType === 'soil' ? 'active' : ''}`}
                >
                  চাষের মাটি
                </button>
                <button
                  type="button"
                  onClick={() => setImageType('auto')}
                  className={`chip-type-tag ${imageType === 'auto' ? 'active' : ''}`}
                >
                  স্বয়ংক্রিয়
                </button>
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClearImage}
            className="btn-cancel-attachment"
            title="ছবি বাতিল করুন"
            aria-label="ছবি বাতিল করুন"
          >
            <X size={18} />
          </button>
        </div>
      )}

      {/* Persistent Bottom Floating Input Bar matching Reference Image */}
      <div className="persistent-bottom-bar">
        {/* Large Green Microphone Button on the Left */}
        <div className={`mic-button-wrapper ${isListening ? 'listening-pulse' : ''}`}>
          {isListening && <div className="concentric-ring ring-outer animate-ping" />}
          {isListening && <div className="concentric-ring ring-inner" />}
          <button
            type="button"
            onClick={toggleVoiceInput}
            className={`btn-primary-mic ${isListening ? 'btn-mic-active' : ''}`}
            aria-label="কথা বলুন (Voice Assistant)"
            title={isListening ? 'কথা বলা থামান ও পাঠান' : 'বাংলায় কথা বলুন'}
          >
            <Mic size={30} className={isListening ? 'animate-bounce' : ''} />
          </button>
        </div>

        {/* Central Pill Input Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            executeSendMessage();
          }}
          className="persistent-input-form"
        >
          <input
            type="text"
            value={inputText || (isListening ? voiceInterimText : '')}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={isListening ? 'শুনছি... বাংলায় বলুন' : 'আপনার প্রশ্ন বলুন...'}
            className="unified-text-field"
            disabled={loading}
          />

          {/* Yellow Circular Camera Button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="btn-primary-camera"
            title="ছবি তুলুন বা আপলোড করুন"
            aria-label="ছবি তুলুন (Camera / Photo)"
          >
            <Camera size={22} />
          </button>

          {/* Hidden File Input for Camera/Gallery */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleImageSelect}
            style={{ display: 'none' }}
          />

          {/* Green Circular Send Button */}
          <button
            type="submit"
            disabled={loading || (!inputText.trim() && !selectedImage)}
            className="btn-primary-send"
            title="জিজ্ঞাসা করুন"
            aria-label="জিজ্ঞাসা করুন"
          >
            {loading ? <RefreshCw size={20} className="animate-spin" /> : <Send size={20} />}
          </button>
        </form>
      </div>
    </div>
  );
}
