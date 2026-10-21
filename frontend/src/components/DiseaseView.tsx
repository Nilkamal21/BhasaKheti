import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  AlertTriangle, 
  CheckCircle2, 
  RotateCcw, 
  ShieldAlert, 
  HelpCircle,
  FileCheck2,
  Sparkles
} from 'lucide-react';
import { predictPlantDisease } from '../services/api';
import type { DiseasePredictionResponse } from '../services/api';

export function DiseaseView() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [result, setResult] = useState<DiseasePredictionResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      
      // Basic client-side check
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
      const response = await predictPlantDisease(selectedFile);
      setResult(response);
    } catch (err: any) {
      setErrorMessage(err.message || 'রোগ নির্ণয় ব্যর্থ হয়েছে। সার্ভারের সাথে সংযোগ নিশ্চিত করুন।');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="card-box disease-container">
      <div className="disease-header">
        <h2 className="card-title">গাছের পাতার রোগ নির্ণয় (Plant Disease Investigation)</h2>
        <p className="card-description">
          আক্রান্ত ফসলের স্পষ্ট পাতার ছবি আপলোড করুন। বর্তমানে মডেলটি <strong>টমেটো, আলু এবং ক্যাপসিকাম</strong>-এর পাতার উপসর্গ বিশ্লেষণের জন্য অনুমোদিত।
        </p>
      </div>

      {/* Upload Zone */}
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
            <UploadCloud size={36} className="text-brand-green" />
          </div>
          <div className="upload-title">আক্রান্ত পাতার ছবি বেছে নিন বা ড্রপ করুন</div>
          <p className="upload-subtitle">JPEG, PNG বা WEBP (সর্বোচ্চ ১০ এমবি)</p>
          <button type="button" className="btn-select-file">
            ছবি নির্বাচন করুন
          </button>
        </div>
      )}

      {/* Image Preview & Actions */}
      {previewUrl && (
        <div className="preview-section">
          <div className="preview-card">
            <img src={previewUrl} alt="নির্বাচিত পাতার ছবি" className="preview-image" />
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
                    <span>রোগ নির্ণয় শুরু করুন</span>
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

      {/* Error Message */}
      {errorMessage && (
        <div className="status-banner banner-warning mt-4">
          <AlertTriangle size={20} className="text-warning-amber" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Prediction Results Display */}
      {result && (
        <div className="results-wrapper">
          <div className="result-main-card">
            <div className="result-badge-row">
              <span className="badge-model-info">{result.model_identifier}</span>
              {result.primary_prediction.is_verified ? (
                <span className="badge-verified">
                  <CheckCircle2 size={14} />
                  <span>যাচাইকৃত লেবেল (Verified Class)</span>
                </span>
              ) : (
                <span className="badge-unverified">
                  <HelpCircle size={14} />
                  <span>যাচাইহীন শ্রেণি (Unverified Mapping)</span>
                </span>
              )}
            </div>

            <div className="result-prediction-title">
              {result.primary_prediction.is_verified ? (
                <>
                  <h3 className="disease-name-bn">
                    {result.primary_prediction.display_name_bn}
                  </h3>
                  <div className="disease-name-en">
                    {result.primary_prediction.display_name_en}
                  </div>
                </>
              ) : (
                <>
                  <h3 className="disease-name-bn text-warning-amber">
                    শ্রেণি ইনডেক্স #{result.primary_prediction.class_index} (যাচাইহীন ম্যাপিং)
                  </h3>
                  <div className="disease-name-en">
                    {result.primary_prediction.raw_class_name}
                  </div>
                </>
              )}
            </div>

            <div className="score-meter-wrap">
              <div className="score-label-row">
                <span>মডেল স্কোর (Model Probability Score):</span>
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

            {/* Top alternative candidates */}
            {result.top_candidates.length > 1 && (
              <div className="candidates-box">
                <div className="candidates-title">অন্যান্য নিকটবর্তী সম্ভাবনা (Alternative Candidates):</div>
                <div className="candidates-list">
                  {result.top_candidates.slice(1).map((cand) => (
                    <div key={cand.class_index} className="candidate-row">
                      <span className="candidate-name">
                        {cand.is_verified ? cand.display_name_bn : `Index #${cand.class_index}`}
                      </span>
                      <span className="candidate-score">
                        {(cand.model_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Mandatory Ethical & Uncertainty Disclaimer */}
          <div className="disclaimer-card">
            <div className="disclaimer-title-row">
              <ShieldAlert size={18} className="text-earth-brown" />
              <strong>গুরুত্বপূর্ণ সীমাবদ্ধতা ও সতর্কবার্তা (Mandatory Safety Notice)</strong>
            </div>
            <p className="disclaimer-text-bn">{result.disclaimer_bn}</p>
            <p className="disclaimer-text-en">{result.disclaimer_en}</p>
            <div className="expert-recommendation">
              <strong>বিশেষজ্ঞ সহায়তা:</strong> নিশ্চিতকরণের জন্য আপনার নিকটস্থ ব্লক কৃষি আধিকারিক (KVK / Krishi Vigyan Kendra) অথবা উপ-কৃষি নির্দেশকের সাথে যোগাযোগ করুন।
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
