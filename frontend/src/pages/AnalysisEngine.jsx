import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { useAuth } from '../hooks/useAuth';
import { certificateAPI } from '../services/api';

export default function AnalysisEngine() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      selectFile(e.dataTransfer.files[0]);
    }
  };

  const selectFile = (f) => {
    const allowed = ['application/pdf', 'image/png', 'image/jpeg'];
    if (!allowed.includes(f.type)) {
      setError('Only PDF, PNG, and JPEG files are supported.');
      return;
    }
    if (f.size > 16 * 1024 * 1024) {
      setError('File must be under 16 MB.');
      return;
    }
    setError('');
    setFile(f);
  };

  const handleSubmit = async () => {
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('certificate', file);
      const res = await certificateAPI.verify(formData);
      const data = res.data;
      navigate(`/report/${data.record_id || data.data?.id || data.id}`);
    } catch (err) {
      setError(err.response?.data?.message || err.message || 'Verification failed');
    } finally {
      setUploading(false);
    }
  };

  const clearFile = () => {
    setFile(null);
    setError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="text-on-surface overflow-x-hidden relative min-h-screen">
      <Sidebar user={user} />

      <main className="ml-20 lg:ml-72 p-4 lg:p-gutter min-h-screen transition-all duration-300">
        {/* Page Header */}
        <div className="mt-6 mb-10 text-left">
          <p className="text-xs font-bold uppercase tracking-widest text-primary/60 mb-2">Document Forensics</p>
          <h2 className="text-3xl lg:text-4xl font-bold tracking-tight text-on-surface">Analysis Engine</h2>
          <p className="text-on-surface-variant/70 mt-2">Upload a certificate or document to verify its authenticity.</p>
        </div>

        {/* Upload Card */}
        <div className="max-w-2xl mx-auto">
          <div
            className={`glass-card rounded-[40px] p-container-padding flex flex-col items-center justify-center text-center relative overflow-hidden group transition-all duration-300 ${
              dragActive ? 'ring-4 ring-primary/40 bg-primary-container/10' : ''
            }`}
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
          >
            {/* Decorative blobs */}
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-primary-container/20 rounded-full blur-3xl" />
            <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-secondary-container/20 rounded-full blur-3xl" />

            <div className="relative z-10 w-full max-w-md py-6">
              {!file ? (
                <>
                  <div className="mb-8 p-10 rounded-[48px] border-2 border-dashed border-primary-container/40 bg-white/20 flex flex-col items-center group-hover:bg-white/40 transition-all duration-500 cursor-pointer"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <div className="w-20 h-20 mb-5 rounded-full bg-gradient-to-br from-white to-primary-container/20 flex items-center justify-center shadow-inner">
                      <span className="material-symbols-outlined text-4xl text-primary" style={{ fontVariationSettings: "'wght' 200" }}>upload_file</span>
                    </div>
                    <h3 className="font-headline-md text-headline-md text-on-surface mb-2">Drop File Here</h3>
                    <p className="font-body-md text-on-surface-variant/60">Supports PDF, PNG, and JPEG (max 16 MB)</p>
                  </div>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    className="hidden"
                    onChange={(e) => e.target.files[0] && selectFile(e.target.files[0])}
                  />

                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="px-10 py-4 rounded-full bg-gradient-to-r from-primary-container to-primary text-white font-bold text-lg shadow-2xl hover:scale-105 active:scale-95 transition-all duration-300 flex items-center justify-center gap-3 mx-auto border-t border-white/30 inner-glow"
                  >
                    <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>folder_open</span>
                    <span>Browse Files</span>
                  </button>
                </>
              ) : (
                <>
                  {/* Selected file preview */}
                  <div className="mb-6 p-6 rounded-3xl bg-white/40 border border-white/60 flex items-center gap-4">
                    <div className="w-14 h-14 rounded-2xl bg-primary-container/20 flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-3xl text-primary">
                        {file.type === 'application/pdf' ? 'picture_as_pdf' : 'image'}
                      </span>
                    </div>
                    <div className="flex-1 text-left min-w-0">
                      <p className="font-bold text-on-surface truncate">{file.name}</p>
                      <p className="text-label-sm text-on-surface-variant/60">{(file.size / 1024).toFixed(1)} KB • {file.type.split('/')[1].toUpperCase()}</p>
                    </div>
                    <button onClick={clearFile} className="p-2 rounded-xl hover:bg-error-container/20 transition-colors" title="Remove file">
                      <span className="material-symbols-outlined text-error">close</span>
                    </button>
                  </div>

                  <button
                    onClick={handleSubmit}
                    disabled={uploading}
                    className={`px-10 py-4 rounded-full text-white font-bold text-lg shadow-2xl transition-all duration-300 flex items-center justify-center gap-3 mx-auto border-t border-white/30 inner-glow ${
                      uploading
                        ? 'bg-on-surface-variant/40 cursor-wait scale-95'
                        : 'bg-gradient-to-r from-primary-container to-primary hover:scale-105 active:scale-95'
                    }`}
                  >
                    {uploading ? (
                      <>
                        <div className="w-5 h-5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                        <span>Analyzing…</span>
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
                        <span>Verify Certificate</span>
                      </>
                    )}
                  </button>
                </>
              )}

              {error && (
                <div className="mt-6 px-4 py-3 rounded-2xl bg-error-container/20 border border-error/20 text-error text-sm font-medium flex items-center gap-2">
                  <span className="material-symbols-outlined text-lg">error</span>
                  {error}
                </div>
              )}
            </div>
          </div>

          {/* Supported formats hint */}
          <div className="mt-8 flex items-center justify-center gap-6 text-on-surface-variant/40 text-label-sm">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-base">picture_as_pdf</span>
              <span>PDF</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-base">image</span>
              <span>PNG</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-base">image</span>
              <span>JPEG</span>
            </div>
          </div>
        </div>
      </main>

      {/* Background Blobs */}
      <div className="fixed top-0 left-0 w-full h-full -z-10 pointer-events-none opacity-40 overflow-hidden">
        <div className="absolute top-[10%] right-[5%] w-96 h-96 bg-primary-container rounded-full blur-[120px] mix-blend-multiply" />
        <div className="absolute bottom-[20%] left-[10%] w-[500px] h-[500px] bg-secondary-container rounded-full blur-[150px] mix-blend-multiply" />
        <div className="absolute top-[40%] left-[30%] w-72 h-72 bg-tertiary-fixed rounded-full blur-[100px] mix-blend-multiply" />
      </div>
    </div>
  );
}
