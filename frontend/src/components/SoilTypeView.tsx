import React, { useState, useRef } from 'react';
import { 
  AlertTriangle, 
  CheckCircle2, 
  RotateCcw, 
  ShieldAlert, 
  HelpCircle,
  FileCheck2,
  Sparkles,
  Layers
} from 'lucide-react';
import { predictSoilType } from '../services/api';
import type { SoilPredictionResponse } from '../services/api';

export function SoilTypeView() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<SoilPredictionResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        setErrorMessage('কেবলমাত্র JPEG, PNG অথবা WEBP ফরম্যাটের ছবি আপলোড করুন।');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setErrorMessage('ছবির আকার সর্বোচ্চ ১০ মেগাবাইটের মধ্যে হতে হবে।');
        return;
      }

      setErrorMessage(null);
      setSelectedFile(file);
      setResult(null);

      const objectUrl = URL.createObjectURL(file);
      setPreviewUrl(objectUrl);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(null);
    setResult(null);
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile) return;

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await predictSoilType(selectedFile);
      setResult(response);
    } catch (err: any) {
      setErrorMessage(err.message || 'মাটির ধরন নির্ণয় ব্যর্থ হয়েছে।');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="card-box disease-container">
      <div className="disease-header">
        <h2 className="card-title">মাটির ধরন বিশ্লেষণ (Soil Type Classification)</h2>
        <p className="card-description">
          মাঠের মাটির পরিষ্কার ছবি আপলোড করুন। মডেলটি ৭টি সাধারণ মাটির ধরন (পলি, শুষ্ক, কৃষ্ণ, ল্যাটারাইট, পার্বত্য, লাল, হলুদ) শনাক্ত করার জন্য প্রস্তুত।
        </p>
      </div>

      {!previewUrl && (
        <div 
          className="upload-dropzone"
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            accept="image/jpeg,image/png,image/webp" 
            style={{ display: 'none' }} 
          />
          <div className="upload-icon-circle">
            <Layers size={36} className="text-brand-green" />
          </div>
          <div className="upload-title">মাটির ছবি নির্বাচন করুন বা ড্রপ করুন</div>
          <p className="upload-subtitle">JPEG, PNG বা WEBP (সর্বোচ্চ ১০ এমবি)</p>
          <button type="button" className="btn-select-file">
            ছবি বেছে নিন
          </button>
        </div>
      )}

      {previewUrl && (
        <div className="preview-section">
          <div className="preview-card">
            <img src={previewUrl} alt="নির্বাচিত মাটির ছবি" className="preview-image" />
            <div className="preview-meta">
              <span className="preview-filename">{selectedFile?.name}</span>
              <span className="preview-filesize">
                {selectedFile ? (selectedFile.size / (1024 * 1024)).toFixed(2) : 0} MB
              </span>
            </div>
          </div>

          <div className="action-buttons-group">
            {!result && (
              <button 
                type="button" 
                onClick={handleSubmit} 
                disabled={isSubmitting} 
                className="btn-submit-predict"
              >
                {isSubmitting ? (
                  <>
                    <Sparkles className="animate-spin" size={18} />
                    <span>বিশ্লেষণ চলছে...</span>
                  </>
                ) : (
                  <>
                    <FileCheck2 size={18} />
                    <span>মাটির ধরন নির্ণয় শুরু করুন</span>
                  </>
                )}
              </button>
            )}

            <button 
              type="button" 
              onClick={handleReset} 
              disabled={isSubmitting} 
              className="btn-reset"
            >
              <RotateCcw size={16} />
              <span>অন্য ছবি পরীক্ষা করুন</span>
            </button>
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="status-banner banner-warning mt-4">
          <AlertTriangle size={20} className="text-warning-amber" />
          <span>{errorMessage}</span>
        </div>
      )}

      {result && (
        <div className="results-wrapper">
          <div className="result-main-card">
            <div className="result-badge-row">
              <span className="badge-model-info">{result.model_identifier}</span>
              {result.primary_prediction.is_verified ? (
                <span className="badge-verified">
                  <CheckCircle2 size={14} />
                  <span>যাচাইকৃত লেবেল (Verified Soil Class)</span>
                </span>
              ) : (
                <span className="badge-unverified">
                  <HelpCircle size={14} />
                  <span>যাচাইহীন শ্রেণি (Unverified Mapping)</span>
                </span>
              )}
            </div>

            <div className="result-prediction-title">
              <h3 className="disease-name-bn">
                {result.primary_prediction.display_name_bn}
              </h3>
              <div className="disease-name-en">
                {result.primary_prediction.display_name_en}
              </div>
            </div>

            <div className="score-meter-wrap">
              <div className="score-label-row">
                <span>মডেল সম্ভাবনা স্কোর:</span>
                <span className="score-number">
                  {(result.primary_prediction.model_score * 100).toFixed(1)}%
                </span>
              </div>
              <div className="score-progress-bar">
                <div 
                  className="score-progress-fill" 
                  style={{ width: `${Math.min(result.primary_prediction.model_score * 100, 100)}%` }}
                />
              </div>
            </div>

            <div className="candidates-box">
              <div className="candidates-title">অন্যান্য সম্ভাব্য মাটির ধরনসমূহ (All Soil Categories):</div>
              <div className="candidates-list">
                {result.all_classes.slice(1).map((cand) => (
                  <div key={cand.class_index} className="candidate-row">
                    <span className="candidate-name">{cand.display_name_bn}</span>
                    <span className="candidate-score">
                      {(cand.model_score * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="disclaimer-card">
            <div className="disclaimer-title-row">
              <ShieldAlert size={18} className="text-earth-brown" />
              <strong>গুরুত্বপূর্ণ বৈজ্ঞানিক সীমাবদ্ধতা (Scientific Limitation)</strong>
            </div>
            <p className="disclaimer-text-bn">{result.disclaimer_bn}</p>
            <p className="disclaimer-text-en">{result.disclaimer_en}</p>
            <div className="expert-recommendation">
              <strong>পরামর্শ:</strong> আপনার খামারের জমির সুনির্দিষ্ট পুষ্টি চাহিদা জানতে নিকটস্থ মাটি পরীক্ষা কেন্দ্র বা কৃষি দফতরে নমুনা পাঠান।
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
