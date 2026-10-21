import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { VoiceAssistant } from '../components/VoiceAssistant';
import * as voiceService from '../services/voiceService';

describe('VoiceAssistant Unit Tests (Phase 8)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders microphone button with Bengali accessibility label', () => {
    render(
      <VoiceAssistant
        onQuestionSubmit={vi.fn()}
        isSubmitting={false}
      />
    );

    const micButton = screen.getByRole('button', { name: /বাংলায় বলুন \(Voice\)/i });
    expect(micButton).toBeInTheDocument();
    expect(screen.getByText(/ভাষা: বাংলা \(ভারত • bn-IN\)/i)).toBeInTheDocument();
    expect(screen.getByText(/কোনো অডিও ফাইল ভাষাখেতি সার্ভারে সংরক্ষণ করা হয় না/i)).toBeInTheDocument();
  });

  it('shows unsupported browser error message when speech recognition is not available', () => {
    vi.spyOn(voiceService, 'checkVoiceCapabilities').mockReturnValue({
      recognitionSupported: false,
      synthesisSupported: false,
      hasBengaliVoice: false,
      isOnline: true
    });

    render(
      <VoiceAssistant
        onQuestionSubmit={vi.fn()}
        isSubmitting={false}
      />
    );

    const micButton = screen.getByRole('button', { name: /বাংলায় বলুন \(Voice\)/i });
    fireEvent.click(micButton);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/আপনার ব্রাউজারে ভয়েস শনাক্তকরণ সুবিধা নেই/i)).toBeInTheDocument();
  });

  it('renders editable transcription preview when speech is recognized', () => {
    vi.spyOn(voiceService, 'checkVoiceCapabilities').mockReturnValue({
      recognitionSupported: true,
      synthesisSupported: true,
      hasBengaliVoice: true,
      isOnline: true
    });

    const mockRecognizer = {
      start: vi.fn(),
      stop: vi.fn(),
      abort: vi.fn()
    };

    vi.spyOn(voiceService, 'createBengaliSpeechRecognizer').mockReturnValue(mockRecognizer as any);

    render(
      <VoiceAssistant
        onQuestionSubmit={vi.fn()}
        isSubmitting={false}
      />
    );

    const micButton = screen.getByRole('button', { name: /বাংলায় বলুন \(Voice\)/i });
    fireEvent.click(micButton);

    expect(mockRecognizer.start).toHaveBeenCalled();
  });

  it('renders Bengali speech synthesis action button when lastAnswerBn is provided', () => {
    const speakSpy = vi.spyOn(voiceService.speechSynthesizer, 'speak').mockReturnValue(true);

    render(
      <VoiceAssistant
        onQuestionSubmit={vi.fn()}
        isSubmitting={false}
        lastAnswerBn="ধানের পাতায় সেচ ও ইউরিয়ার ভারসাম্য রক্ষা করুন।"
      />
    );

    const ttsButton = screen.getByRole('button', { name: /পরামর্শটি বাংলায় শুনুন/i });
    expect(ttsButton).toBeInTheDocument();

    fireEvent.click(ttsButton);
    expect(speakSpy).toHaveBeenCalled();
  });

  it('stops speech synthesis when stop button or unmount is triggered', () => {
    const stopSpy = vi.spyOn(voiceService.speechSynthesizer, 'stop');

    const { unmount } = render(
      <VoiceAssistant
        onQuestionSubmit={vi.fn()}
        isSubmitting={false}
        lastAnswerBn="ধানের পাতায় সেচ ও ইউরিয়ার ভারসাম্য রক্ষা করুন।"
      />
    );

    unmount();
    expect(stopSpy).toHaveBeenCalled();
  });

  it('allows editing transcription before submission and submits edited text', () => {
    vi.spyOn(voiceService, 'checkVoiceCapabilities').mockReturnValue({
      recognitionSupported: true,
      synthesisSupported: true,
      hasBengaliVoice: true,
      isOnline: true
    });

    const handleSubmit = vi.fn();
    const mockRecognizer = {
      start: vi.fn(),
      stop: vi.fn(),
      abort: vi.fn()
    };

    let savedCallbacks: any = null;
    vi.spyOn(voiceService, 'createBengaliSpeechRecognizer').mockImplementation((callbacks: any) => {
      savedCallbacks = callbacks;
      return mockRecognizer as any;
    });

    render(
      <VoiceAssistant
        onQuestionSubmit={handleSubmit}
        isSubmitting={false}
      />
    );

    const micButton = screen.getByRole('button', { name: /বাংলায় বলুন \(Voice\)/i });
    fireEvent.click(micButton);

    // Simulate recognized speech inside act
    act(() => {
      savedCallbacks.onStart();
      savedCallbacks.onResult('ধানের পোকা', true);
    });

    const textarea = screen.getByLabelText(/শনাক্তকৃত প্রশ্নের লিখিত রূপ/i);
    expect(textarea).toBeInTheDocument();

    // Farmer edits the text before submitting
    act(() => {
      fireEvent.change(textarea, { target: { value: 'ধানের মাজরা পোকা দমনে কী করব?' } });
    });

    const submitBtn = screen.getByRole('button', { name: /এই প্রশ্নটি জিজ্ঞাসা করুন/i });
    act(() => {
      fireEvent.click(submitBtn);
    });

    expect(handleSubmit).toHaveBeenCalledWith('ধানের মাজরা পোকা দমনে কী করব?');
  });
});
