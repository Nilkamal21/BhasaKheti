import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SupervisorHomeView } from '../components/SupervisorHomeView';
import * as api from '../services/api';
import * as voiceService from '../services/voiceService';

vi.mock('../services/api', () => ({
  sendSupervisorMessage: vi.fn()
}));

describe('SupervisorHomeView Redesigned Unit & Integration Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders first-time welcome greeting, 4 visual suggestion cards, and persistent bottom bar', () => {
    render(<SupervisorHomeView />);

    // 1. First-time welcome greeting matching reference image
    expect(screen.getByRole('heading', { level: 2, name: /নমস্কার!/i })).toBeInTheDocument();
    expect(screen.getByText(/আপনি কী জানতে চান\?/i)).toBeInTheDocument();

    // 2. Four Visual Suggestion Cards
    expect(screen.getByRole('button', { name: /ধানের সমস্যা/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /বৃষ্টি ও আবহাওয়া/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /আজকের বাজারদর/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /সরকারি প্রকল্প/i })).toBeInTheDocument();

    // 3. Persistent Unified Bottom Bar
    const micBtn = screen.getByRole('button', { name: /কথা বলুন \(Voice Assistant\)/i });
    expect(micBtn).toBeInTheDocument();

    const cameraBtn = screen.getByRole('button', { name: /ছবি তুলুন \(Camera \/ Photo\)/i });
    expect(cameraBtn).toBeInTheDocument();

    expect(screen.getByPlaceholderText(/আপনার প্রশ্ন বলুন\.\.\./i)).toBeInTheDocument();
    expect(screen.getByTitle('জিজ্ঞাসা করুন')).toBeInTheDocument();
  });

  it('immediately triggers Bengali speech recognition on microphone button click', () => {
    const mockRecognizer = {
      start: vi.fn(),
      stop: vi.fn(),
      abort: vi.fn()
    };
    vi.spyOn(voiceService, 'createBengaliSpeechRecognizer').mockReturnValue(mockRecognizer as any);

    render(<SupervisorHomeView />);

    const micBtn = screen.getByRole('button', { name: /কথা বলুন \(Voice Assistant\)/i });
    fireEvent.click(micBtn);

    expect(voiceService.createBengaliSpeechRecognizer).toHaveBeenCalled();
    expect(mockRecognizer.start).toHaveBeenCalled();
  });

  it('submits a visual suggestion card, routes through supervisor and renders tools, citations, and TTS button', async () => {
    const mockResponse: api.SupervisorChatResponse = {
      answer_bn: 'ধানের মাজরা পোকা ও পাতা ধসা দমনে নিয়মিত পর্যবেক্ষণ করুন। আগামী ৪৮ ঘণ্টায় কোনো ভারী বৃষ্টি নেই।',
      intent: 'disease_inquiry',
      tools_invoked: ['predict_plant_disease', 'get_weather'],
      follow_up_prompt_bn: 'আপনি কি ধানের জমিতে সেচ প্রদান করেছেন?',
      citations: [
        {
          id: 'KB-RICE-001',
          title_bn: 'ধানের সমন্বিত বালাই ব্যবস্থাপনা',
          source_org: 'ICAR-NRRI',
          source_url: 'https://icar-nrri.gov.in'
        }
      ],
      safety_warnings: ['কীটনাশক প্রয়োগের সময় সতর্ক থাকুন ও মাস্ক পরুন।'],
      detected_crop: 'rice',
      llm_used: true,
      provider: 'deterministic'
    };

    vi.spyOn(api, 'sendSupervisorMessage').mockResolvedValue(mockResponse);

    render(<SupervisorHomeView />);

    const paddyCard = screen.getByRole('button', { name: /ধানের সমস্যা/i });
    fireEvent.click(paddyCard);

    // Verify loading or response
    await waitFor(() => {
      expect(screen.getByText(/ধানের মাজরা পোকা ও পাতা ধসা দমনে নিয়মিত পর্যবেক্ষণ করুন/i)).toBeInTheDocument();
      expect(screen.getByText('ICAR-NRRI')).toBeInTheDocument();
      expect(screen.getByText(/কীটনাশক প্রয়োগের সময় সতর্ক থাকুন ও মাস্ক পরুন/i)).toBeInTheDocument();
      expect(screen.getByText('আপনি কি ধানের জমিতে সেচ প্রদান করেছেন?')).toBeInTheDocument();
      expect(screen.getByTitle('পরামর্শ বাংলায় শুনুন')).toBeInTheDocument();
    });

    expect(api.sendSupervisorMessage).toHaveBeenCalledTimes(1);
  });

  it('renders image attachment preview and allows changing image type', () => {
    const { container } = render(<SupervisorHomeView />);

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeInTheDocument();

    // Create a mock image file
    const file = new File(['mock content'], 'leaf.jpg', { type: 'image/jpeg' });
    global.URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-leaf-preview');

    fireEvent.change(fileInput, { target: { files: [file] } });

    // Verify thumbnail is displayed
    expect(screen.getByText(/নির্বাচিত ছবি প্রস্তুত/i)).toBeInTheDocument();
    const thumbnail = screen.getByAltText('নির্বাচিত ছবি');
    expect(thumbnail).toHaveAttribute('src', 'blob:mock-leaf-preview');

    // Change image type
    const soilTypeBtn = screen.getByRole('button', { name: 'চাষের মাটি' });
    fireEvent.click(soilTypeBtn);
    expect(soilTypeBtn).toHaveClass('active');

    // Clear image
    const removeBtn = screen.getByTitle('ছবি বাতিল করুন');
    fireEvent.click(removeBtn);
    expect(screen.queryByText(/নির্বাচিত ছবি প্রস্তুত/i)).not.toBeInTheDocument();
  });
});
