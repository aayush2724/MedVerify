import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2, ArrowLeft } from 'lucide-react';
import { getRecord } from '../services/api';
import ResultCard from '../components/ResultCard';

const ReportPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [record, setRecord] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchRecord = async () => {
      try {
        const { data } = await getRecord(id);
        // Map backend record to match ResultCard expectations
        setRecord({
          record_id: data.id,
          status: data.status,
          confidence_score: data.confidence,
          reasons: data.reasons,
          model_version: data.model_version || '1.0.0',
          decision_logic: data.decision_logic || {},
          extracted_info: data.extracted_fields || {}
        });
      } catch {
        setError('Failed to load verification report');
      } finally {
        setIsLoading(false);
      }
    };
    fetchRecord();
  }, [id]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="animate-spin text-primary mb-4" size={48} />
        <p className="text-slate-500 font-medium">Retrieving secure audit record...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-6 max-w-4xl">
      <button 
        onClick={() => navigate('/history')}
        className="flex items-center gap-2 text-slate-500 hover:text-primary transition-colors font-bold mb-8"
      >
        <ArrowLeft size={20} /> Back to Audit Log
      </button>

      {error ? (
        <div className="bg-red-50 p-8 rounded-3xl text-center">
          <p className="text-red-600 font-bold mb-2">Error</p>
          <p className="text-slate-600">{error}</p>
        </div>
      ) : (
        <ResultCard result={record} onReset={() => navigate('/')} />
      )}
    </div>
  );
};

export default ReportPage;
