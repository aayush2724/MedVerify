import { useState, useEffect } from 'react';
import { Upload, CheckCircle2, AlertCircle, Loader2, FileCheck, Search, Image as ImageIcon, Database, Files, FileText, XCircle, ShieldCheck } from 'lucide-react';
import { verifyCertificate, getTaskStatus } from '../services/api';
import ResultCard from '../components/ResultCard';

const steps = [
  { id: 'upload', label: 'Uploading', icon: Upload },
  { id: 'preprocess', label: 'Preprocessing', icon: ImageIcon },
  { id: 'ocr', label: 'OCR Extraction', icon: FileCheck },
  { id: 'analyze', label: 'AI Analysis', icon: Search },
  { id: 'persist', label: 'Finalizing', icon: Database },
];

const VerifyPage = () => {
  const [queue, setQueue] = useState([]); // { file, status, progress, step, result, error, taskId }
  const [isProcessing, setIsProcessing] = useState(false);

  const handleFileChange = (e) => {
    const selected = Array.from(e.target.files);
    if (selected.length > 0) {
      const newEntries = selected.map(file => ({
        file,
        status: 'READY',
        progress: 0,
        step: 0,
        result: null,
        error: null,
        taskId: null
      }));
      setQueue(prev => [...prev, ...newEntries]);
    }
  };

  const processFile = async (index) => {
    const entry = queue[index];
    updateEntry(index, { status: 'UPLOADING', step: 0 });

    try {
      const { data } = await verifyCertificate(entry.file, (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        updateEntry(index, { progress: percentCompleted });
        if (percentCompleted === 100) updateEntry(index, { status: 'PROCESSING', step: 1 });
      });

      updateEntry(index, { taskId: data.task_id });
    } catch (err) {
      updateEntry(index, { status: 'ERROR', error: err.response?.data?.error || 'Upload failed' });
    }
  };

  const updateEntry = (index, updates) => {
    setQueue(prev => {
      const next = [...prev];
      next[index] = { ...next[index], ...updates };
      return next;
    });
  };

  const startBatch = () => {
    setIsProcessing(true);
    queue.forEach((_, idx) => {
      if (queue[idx].status === 'READY') processFile(idx);
    });
  };

  useEffect(() => {
    const pollers = queue.map((entry, idx) => {
      if (entry.taskId && entry.status === 'PROCESSING') {
        return setInterval(async () => {
          try {
            const { data } = await getTaskStatus(entry.taskId);
            if (data.status === 'SUCCESS') {
              updateEntry(idx, { status: 'COMPLETED', result: data.result, step: 4, taskId: null });
            } else if (data.status === 'FAILURE') {
              updateEntry(idx, { status: 'ERROR', error: data.error, taskId: null });
            } else {
              // Simulate step progression
              updateEntry(idx, { step: Math.min(entry.step + 1, 3) });
            }
          } catch {
            updateEntry(idx, { status: 'ERROR', error: 'Polling error', taskId: null });
          }
        }, 2000);
      }
      return null;
    });

    return () => pollers.forEach(p => p && clearInterval(p));
  }, [queue]);

  const removeFile = (index) => {
    setQueue(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="container mx-auto px-6 max-w-5xl">
      <div className="text-center mb-12">
        <h2 className="text-4xl font-bold text-slate-900 mb-4">Batch Validation Portal</h2>
        <p className="text-slate-500 text-lg">Verify multiple medical certificates simultaneously with full audit compliance.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        <div className="lg:col-span-1">
          <div 
            className="bg-white border-2 border-dashed border-slate-200 rounded-3xl p-8 text-center hover:border-primary transition-colors cursor-pointer"
            onClick={() => document.getElementById('fileInput').click()}
          >
            <input type="file" id="fileInput" hidden multiple onChange={handleFileChange} accept=".pdf,.png,.jpg,.jpeg" />
            <Files size={48} className="mx-auto mb-4 text-primary opacity-20" />
            <h3 className="font-bold text-slate-900 mb-2">Select Documents</h3>
            <p className="text-sm text-slate-500 mb-6">Drop multiple files here</p>
            <button className="btn btn-secondary w-full">Browse Files</button>
          </div>

          {queue.length > 0 && (
            <div className="mt-8 space-y-3">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest px-2">Queue ({queue.length})</h4>
              {queue.map((entry, idx) => (
                <div key={idx} className="bg-white p-3 rounded-xl border border-slate-100 flex items-center justify-between shadow-sm">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <FileText size={18} className="text-slate-400 shrink-0" />
                    <span className="text-sm font-semibold truncate text-slate-700">{entry.file.name}</span>
                  </div>
                  {entry.status === 'READY' && (
                    <button onClick={() => removeFile(idx)} className="text-slate-300 hover:text-danger">
                      <XCircle size={16} />
                    </button>
                  )}
                  {entry.status === 'COMPLETED' && <CheckCircle2 size={16} className="text-success" />}
                  {entry.status === 'ERROR' && <AlertCircle size={16} className="text-danger" />}
                  {(entry.status === 'UPLOADING' || entry.status === 'PROCESSING') && <Loader2 size={16} className="text-primary animate-spin" />}
                </div>
              ))}
              <button 
                onClick={startBatch} 
                disabled={isProcessing || queue.every(e => e.status !== 'READY')}
                className="btn btn-primary w-full mt-4 py-4"
              >
                Verify {queue.filter(e => e.status === 'READY').length} Files
              </button>
            </div>
          )}
        </div>

        <div className="lg:col-span-2 space-y-6">
          {queue.filter(e => e.status !== 'READY').length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center text-slate-300 border-2 border-dashed rounded-3xl">
              <ShieldCheck size={64} className="mb-4 opacity-10" />
              <p className="font-medium">No active verifications</p>
            </div>
          ) : (
            queue.filter(e => e.status !== 'READY').map((entry, idx) => (
              <div key={idx} className="fade-in">
                {entry.status === 'COMPLETED' ? (
                  <ResultCard result={entry.result} onReset={() => removeFile(idx)} isBatch />
                ) : entry.status === 'ERROR' ? (
                  <div className="bg-red-50 p-6 rounded-3xl border border-red-100 flex items-start gap-4 text-red-700">
                    <AlertCircle className="shrink-0" />
                    <div className="flex-1">
                      <p className="font-bold">{entry.file.name}</p>
                      <p className="text-sm opacity-90">{entry.error}</p>
                      <button onClick={() => processFile(idx)} className="mt-2 text-xs font-bold uppercase tracking-widest border-b border-red-200">Retry</button>
                    </div>
                  </div>
                ) : (
                  <div className="bg-white p-6 rounded-3xl border border-slate-100 shadow-lg">
                    <div className="flex justify-between items-center mb-6">
                      <h4 className="font-bold text-slate-900 truncate pr-4">{entry.file.name}</h4>
                      <span className="text-xs font-bold text-primary uppercase tracking-widest">{steps[entry.step].label}</span>
                    </div>
                    <div className="flex gap-2 mb-4">
                      {steps.map((_, sIdx) => (
                        <div key={sIdx} className={`h-1.5 flex-1 rounded-full ${sIdx <= entry.step ? 'bg-primary' : 'bg-slate-100'}`} />
                      ))}
                    </div>
                    {entry.status === 'UPLOADING' && (
                      <div className="flex items-center gap-4">
                        <div className="flex-1 bg-slate-100 h-1 rounded-full overflow-hidden">
                          <div className="bg-primary h-full transition-all duration-300" style={{ width: `${entry.progress}%` }} />
                        </div>
                        <span className="text-[10px] font-bold text-slate-400">{entry.progress}%</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default VerifyPage;
