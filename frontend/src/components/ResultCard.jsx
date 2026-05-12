import { CheckCircle2, AlertTriangle, XCircle, FileDown, RotateCcw, Info, Database } from 'lucide-react';
import { motion } from 'framer-motion';
import jsPDF from 'jspdf';

const statusConfig = {
  GENUINE: { icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100' },
  SUSPICIOUS: { icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100' },
  FAKE: { icon: XCircle, color: 'text-rose-600', bg: 'bg-rose-50', border: 'border-rose-100' },
};

const ResultCard = ({ result, onReset }) => {
  const config = statusConfig[result.status] || statusConfig.SUSPICIOUS;
  const Icon = config.icon;

  const downloadReport = () => {
    const doc = new jsPDF();
    doc.setFontSize(22);
    doc.text('CertSentinel Verification Report', 20, 20);
    doc.setFontSize(12);
    doc.text(`Record ID: ${result.record_id}`, 20, 30);
    doc.text(`Status: ${result.status}`, 20, 40);
    doc.text(`Confidence: ${Math.round(result.confidence_score * 100)}%`, 20, 50);
    doc.text(`Model Version: ${result.model_version}`, 20, 60);
    
    doc.text('Detected Issues:', 20, 80);
    result.reasons.forEach((reason, i) => {
      doc.text(`- ${reason}`, 25, 90 + (i * 10));
    });
    
    doc.save(`CertSentinel_Report_${result.record_id}.pdf`);
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="mt-12 bg-white rounded-3xl border border-slate-100 shadow-2xl overflow-hidden"
    >
      <div className={`${config.bg} p-8 border-b ${config.border} flex justify-between items-center`}>
        <div className="flex items-center gap-4">
          <div className={`${config.color} bg-white p-3 rounded-2xl shadow-sm`}>
            <Icon size={32} />
          </div>
          <div>
            <h3 className={`text-2xl font-bold ${config.color}`}>{result.status}</h3>
            <p className="text-slate-500 font-medium">Authenticity Verdict</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-slate-900">{Math.round(result.confidence_score * 100)}%</div>
          <p className="text-slate-500 text-sm font-bold uppercase tracking-wider">Confidence Score</p>
        </div>
      </div>

      <div className="p-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              <Info size={16} /> Reasoning Engine
            </h4>
            <ul className="space-y-3">
              {result.reasons.map((reason, i) => (
                <li key={i} className="flex items-start gap-3 text-slate-700 bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <div className="w-1.5 h-1.5 bg-primary rounded-full mt-2 shrink-0" />
                  {reason}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              <Database size={16} /> Technical Logic
            </h4>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-600 text-sm">Text Authenticity</span>
                <span className="font-bold text-slate-900">{Math.round(result.decision_logic.text_score * 100)}%</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-600 text-sm">Visual Integrity</span>
                <span className="font-bold text-slate-900">{Math.round(result.decision_logic.image_score * 100)}%</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-600 text-sm">Model Version</span>
                <span className="font-bold text-slate-900">{result.model_version}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-10 flex gap-4 border-t pt-8">
          <button onClick={downloadReport} className="btn btn-primary flex-1">
            <FileDown size={20} /> Export PDF Report
          </button>
          <button onClick={onReset} className="btn btn-outline">
            <RotateCcw size={20} /> Verify Another
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export default ResultCard;
