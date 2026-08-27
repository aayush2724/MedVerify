import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import { medicationAPI } from '../services/api';
import { useAuth } from '../hooks/useAuth';

export default function MyMedications() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [medications, setMedications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(null);

  // Refetch without touching the spinner — used to roll back an optimistic
  // update that the server rejected.
  const load = useCallback(async () => {
    try {
      const res = await medicationAPI.list();
      setMedications(res.data.medications || []);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.message || 'Could not load your medication list.');
    }
  }, []);

  useEffect(() => {
    if (!user) return;
    const loadInitial = async () => {
      setLoading(true);
      await load();
      setLoading(false);
    };
    loadInitial();
  }, [user, load]);

  const handleRemove = async (id) => {
    setMedications((prev) => prev.filter((m) => m.id !== id));
    try {
      await medicationAPI.remove(id);
    } catch {
      load(); // put it back if the server disagreed
    }
  };

  const handleDoseSave = async (id, unitsPerDose, dosesPerDay) => {
    try {
      const res = await medicationAPI.update(id, {
        units_per_dose: unitsPerDose,
        doses_per_day: dosesPerDay,
      });
      setMedications((prev) => prev.map((m) => (m.id === id ? res.data : m)));
      setEditing(null);
    } catch (err) {
      setError(err.response?.data?.message || 'Could not update that dose.');
    }
  };

  const handleRunCheck = async () => {
    setChecking(true);
    setError(null);
    try {
      const res = await medicationAPI.runSafetyCheck();
      navigate('/medications/report', { state: { result: res.data } });
    } catch (err) {
      setError(err.response?.data?.message || 'The safety check could not be completed.');
      setChecking(false);
    }
  };

  const unmatchedCount = medications.filter((m) => !m.rxcui).length;

  return (
    <div className="min-h-screen">
      <Sidebar user={user} />
      <main className="ml-20 lg:ml-72 p-6 lg:p-container-padding transition-all duration-300">
        <div className="max-w-5xl mx-auto">

          <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-primary/60 mb-2">
                Medication Safety
              </p>
              <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-on-surface">
                My Medications
              </h1>
              <p className="text-on-surface-variant/70 mt-2 max-w-xl">
                Add everything you take — prescription and over-the-counter — and MedVerify
                will check the list for repeated ingredients and daily totals.
              </p>
            </div>
            <button
              onClick={() => navigate('/medications/add')}
              className="py-3 px-5 rounded-2xl bg-gradient-to-r from-primary to-primary-container text-white font-bold shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2"
            >
              <span className="material-symbols-outlined">add</span>
              Add medication
            </button>
          </header>

          {/* The framing that keeps this an informational tool. Deliberately
              above the list, not buried in a footer. */}
          <div className="mb-6 rounded-2xl border border-primary/15 bg-white/60 backdrop-blur-xl p-4 flex gap-3">
            <span className="material-symbols-outlined text-primary shrink-0">info</span>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              This is an <strong>informational check</strong> against published FDA label and
              RxNorm data — not medical advice, and not a review of your medical history.
              It cannot see your allergies, conditions, or anything a doctor has told you.
              Always confirm with a pharmacist or doctor.
            </p>
          </div>

          {error && (
            <div className="mb-6 rounded-2xl border border-error/20 bg-error-container/30 p-4 text-error text-sm font-medium">
              {error}
            </div>
          )}

          {loading ? (
            <div className="space-y-3">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-24 rounded-2xl bg-white/40 animate-pulse" />
              ))}
            </div>
          ) : medications.length === 0 ? (
            <EmptyState onAdd={() => navigate('/medications/add')} />
          ) : (
            <>
              <div className="space-y-3">
                <AnimatePresence initial={false}>
                  {medications.map((med) => (
                    <MedicationRow
                      key={med.id}
                      med={med}
                      isEditing={editing === med.id}
                      onEdit={() => setEditing(med.id)}
                      onCancelEdit={() => setEditing(null)}
                      onSave={handleDoseSave}
                      onRemove={handleRemove}
                    />
                  ))}
                </AnimatePresence>
              </div>

              {unmatchedCount > 0 && (
                <p className="mt-4 text-sm text-on-surface-variant/70 flex items-center gap-2">
                  <span className="material-symbols-outlined text-base">help</span>
                  {unmatchedCount} item{unmatchedCount > 1 ? 's' : ''} could not be matched to a
                  known product, so {unmatchedCount > 1 ? 'their' : 'its'} ingredients are unknown
                  and will be reported as unchecked.
                </p>
              )}

              <div className="mt-8 rounded-3xl border border-white/40 bg-white/60 backdrop-blur-2xl p-6 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h3 className="font-bold text-on-surface text-lg">Run a safety check</h3>
                  <p className="text-sm text-on-surface-variant/70">
                    Checks all {medications.length} item{medications.length > 1 ? 's' : ''} for
                    repeated active ingredients and combined daily totals.
                  </p>
                </div>
                <button
                  onClick={handleRunCheck}
                  disabled={checking}
                  className="py-4 px-7 rounded-2xl bg-gradient-to-r from-primary to-primary-container text-white font-bold shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-60 disabled:hover:scale-100 flex items-center gap-2"
                >
                  <span className={`material-symbols-outlined ${checking ? 'animate-spin' : ''}`}>
                    {checking ? 'progress_activity' : 'health_and_safety'}
                  </span>
                  {checking ? 'Checking…' : 'Check my medications'}
                </button>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function MedicationRow({ med, isEditing, onEdit, onCancelEdit, onSave, onRemove }) {

  const dailyTotals = med.ingredients
    .filter((i) => i.strength_mg)
    .map((i) => ({
      name: i.name,
      mg: Math.round(i.strength_mg * med.units_per_dose * med.doses_per_day * 100) / 100,
    }));

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0, marginBottom: 0 }}
      className="rounded-2xl border border-white/40 bg-white/60 backdrop-blur-2xl p-5"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-bold text-on-surface truncate">{med.display_name}</h3>
            {!med.rxcui && (
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full bg-surface-container-high text-on-surface-variant/70">
                Unmatched
              </span>
            )}
            {med.entry_source === 'ocr' && (
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full bg-primary-fixed text-on-primary-fixed">
                From photo
              </span>
            )}
          </div>

          {med.ingredients.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {med.ingredients.map((ing) => (
                <span
                  key={ing.key}
                  className="text-xs px-2.5 py-1 rounded-lg bg-primary-fixed/60 text-on-primary-fixed font-medium"
                >
                  {ing.name}{ing.strength_display ? ` · ${ing.strength_display}` : ''}
                </span>
              ))}
            </div>
          )}

          {isEditing ? (
            <DoseEditForm med={med} onSave={onSave} onCancel={onCancelEdit} />
          ) : (
            <p className="mt-3 text-sm text-on-surface-variant">
              {med.units_per_dose} per dose · {med.doses_per_day} time
              {med.doses_per_day === 1 ? '' : 's'} a day
              {dailyTotals.length > 0 && (
                <span className="text-on-surface-variant/60">
                  {' — '}
                  {dailyTotals.map((t) => `${t.mg} mg ${t.name}`).join(', ')} daily
                </span>
              )}
            </p>
          )}
        </div>

        <div className="flex gap-1 shrink-0">
          {!isEditing && (
            <button onClick={onEdit} title="Edit dose"
              className="p-2 rounded-xl hover:bg-primary-fixed/50 text-on-surface-variant/60 hover:text-primary transition-colors">
              <span className="material-symbols-outlined">edit</span>
            </button>
          )}
          <button onClick={() => onRemove(med.id)} title="Remove"
            className="p-2 rounded-xl hover:bg-error-container/40 text-on-surface-variant/60 hover:text-error transition-colors">
            <span className="material-symbols-outlined">delete</span>
          </button>
        </div>
      </div>
    </motion.div>
  );
}

/** Mounted only while editing, so its draft state is always seeded fresh
    from the saved values — a cancelled edit leaves nothing stale behind. */
function DoseEditForm({ med, onSave, onCancel }) {
  const [units, setUnits] = useState(med.units_per_dose);
  const [perDay, setPerDay] = useState(med.doses_per_day);

  return (
    <div className="mt-4 flex flex-wrap items-end gap-3">
      <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant/60">
        Units per dose
        <input
          type="number" min="0.25" step="0.25" value={units}
          onChange={(e) => setUnits(e.target.value)}
          className="mt-1 block w-28 rounded-xl border border-outline-variant bg-white px-3 py-2 text-sm font-normal text-on-surface normal-case tracking-normal"
        />
      </label>
      <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant/60">
        Doses per day
        <input
          type="number" min="0.25" step="0.25" value={perDay}
          onChange={(e) => setPerDay(e.target.value)}
          className="mt-1 block w-28 rounded-xl border border-outline-variant bg-white px-3 py-2 text-sm font-normal text-on-surface normal-case tracking-normal"
        />
      </label>
      <button
        onClick={() => onSave(med.id, Number(units), Number(perDay))}
        className="px-4 py-2 rounded-xl bg-primary text-white text-sm font-bold"
      >
        Save
      </button>
      <button onClick={onCancel} className="px-4 py-2 rounded-xl text-sm font-bold text-on-surface-variant">
        Cancel
      </button>
    </div>
  );
}

function EmptyState({ onAdd }) {
  return (
    <div className="rounded-3xl border border-white/40 bg-white/60 backdrop-blur-2xl p-12 text-center">
      <div className="w-16 h-16 mx-auto rounded-2xl bg-primary-fixed flex items-center justify-center mb-4">
        <span className="material-symbols-outlined text-primary text-3xl">pill</span>
      </div>
      <h3 className="text-xl font-bold text-on-surface">Your list is empty</h3>
      <p className="text-on-surface-variant/70 mt-2 max-w-md mx-auto">
        Add the medicines you take — including painkillers, cold and flu remedies and sleep
        aids. Those combination products are where repeated ingredients usually hide.
      </p>
      <button onClick={onAdd}
        className="mt-6 py-3 px-6 rounded-2xl bg-gradient-to-r from-primary to-primary-container text-white font-bold shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all">
        Add your first medication
      </button>
    </div>
  );
}
