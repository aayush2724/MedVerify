import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import { medicationAPI } from '../services/api';
import { useAuth } from '../hooks/useAuth';

const TABS = [
  { id: 'search', label: 'Search by name', icon: 'search' },
  { id: 'scan', label: 'Scan the package', icon: 'photo_camera' },
];

export default function AddMedication() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [tab, setTab] = useState('search');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);

  // Debounced so typing doesn't fire a request per keystroke.
  useEffect(() => {
    if (tab !== 'search') return undefined;
    const term = query.trim();

    // Clearing happens inside the timer too, so the effect body performs no
    // synchronous state update (react-hooks/set-state-in-effect).
    const handle = setTimeout(async () => {
      if (term.length < 2) { setResults([]); return; }
      setSearching(true);
      try {
        const res = await medicationAPI.search(term);
        setResults(res.data.results || []);
        setError(null);
      } catch (err) {
        setError(err.response?.data?.message || 'Search is unavailable right now.');
      } finally {
        setSearching(false);
      }
    }, 350);

    return () => clearTimeout(handle);
  }, [query, tab]);

  return (
    <div className="min-h-screen">
      <Sidebar user={user} />
      <main className="ml-20 lg:ml-72 p-6 lg:p-container-padding transition-all duration-300">
        <div className="max-w-3xl mx-auto">

          <button onClick={() => navigate('/medications')}
            className="mb-6 flex items-center gap-2 text-sm font-bold text-on-surface-variant/70 hover:text-primary transition-colors">
            <span className="material-symbols-outlined text-base">arrow_back</span>
            Back to my medications
          </button>

          <h1 className="text-3xl font-bold tracking-tight text-on-surface mb-2">Add a medication</h1>
          <p className="text-on-surface-variant/70 mb-8">
            Matching your product to its official RxNorm entry is what lets MedVerify see the
            active ingredients inside it.
          </p>

          <div className="flex gap-2 mb-6">
            {TABS.map((t) => (
              <button key={t.id} onClick={() => { setTab(t.id); setError(null); }}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-2xl font-bold text-sm transition-all ${
                  tab === t.id
                    ? 'bg-primary text-white shadow-lg shadow-primary/20'
                    : 'bg-white/60 text-on-surface-variant hover:bg-white/80'
                }`}>
                <span className="material-symbols-outlined text-base">{t.icon}</span>
                {t.label}
              </button>
            ))}
          </div>

          {error && (
            <div className="mb-6 rounded-2xl border border-error/20 bg-error-container/30 p-4 text-error text-sm font-medium">
              {error}
            </div>
          )}

          {tab === 'search' ? (
            <SearchPanel
              query={query} setQuery={setQuery} results={results}
              searching={searching} onSelect={setSelected}
            />
          ) : (
            <ScanPanel onSelect={setSelected} setError={setError} />
          )}

          {selected && (
            <DoseDialog
              product={selected}
              onClose={() => setSelected(null)}
              onAdded={() => navigate('/medications')}
              setError={setError}
            />
          )}
        </div>
      </main>
    </div>
  );
}

function SearchPanel({ query, setQuery, results, searching, onSelect }) {
  return (
    <>
      <div className="relative mb-4">
        <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant/50">
          search
        </span>
        <input
          autoFocus value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. Tylenol Extra Strength, ibuprofen 200 mg…"
          className="w-full rounded-2xl border border-white/40 bg-white/70 backdrop-blur-xl py-4 pl-12 pr-4 text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/30"
        />
        {searching && (
          <span className="material-symbols-outlined animate-spin absolute right-4 top-1/2 -translate-y-1/2 text-primary">
            progress_activity
          </span>
        )}
      </div>

      {query.trim().length >= 2 && !searching && results.length === 0 && (
        <p className="text-sm text-on-surface-variant/70 px-2">
          No product matched that name. Check the spelling on the package, or try the active
          ingredient instead of the brand.
        </p>
      )}

      <div className="space-y-2">
        {results.map((r) => (
          <button key={r.rxcui} onClick={() => onSelect(r)}
            className="w-full text-left rounded-2xl border border-white/40 bg-white/60 backdrop-blur-2xl p-4 hover:border-primary/30 hover:bg-white/80 transition-all group">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="font-bold text-on-surface truncate">{r.name}</p>
                <p className="text-xs text-on-surface-variant/60 mt-0.5">
                  {r.is_branded ? 'Brand product' : 'Generic product'} · RxCUI {r.rxcui} · {r.source}
                </p>
              </div>
              <span className="material-symbols-outlined text-on-surface-variant/40 group-hover:text-primary transition-colors shrink-0">
                add_circle
              </span>
            </div>
          </button>
        ))}
      </div>

      <p className="mt-6 text-xs text-on-surface-variant/50 px-2">
        Product data from RxNorm, US National Library of Medicine.
      </p>
    </>
  );
}

function ScanPanel({ onSelect, setError }) {
  const fileRef = useRef(null);
  const [scanning, setScanning] = useState(false);
  const [scan, setScan] = useState(null);

  const handleFile = async (file) => {
    if (!file) return;
    setScanning(true);
    setScan(null);
    try {
      const res = await medicationAPI.scan(file);
      setScan(res.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.message || 'That photo could not be read.');
    } finally {
      setScanning(false);
    }
  };

  return (
    <>
      <div
        onClick={() => fileRef.current?.click()}
        className="rounded-3xl border-2 border-dashed border-primary/25 bg-white/50 backdrop-blur-xl p-10 text-center cursor-pointer hover:border-primary/50 hover:bg-white/70 transition-all"
      >
        <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])} />
        <div className="w-14 h-14 mx-auto rounded-2xl bg-primary-fixed flex items-center justify-center mb-3">
          <span className={`material-symbols-outlined text-primary text-3xl ${scanning ? 'animate-spin' : ''}`}>
            {scanning ? 'progress_activity' : 'photo_camera'}
          </span>
        </div>
        <p className="font-bold text-on-surface">
          {scanning ? 'Reading the package…' : 'Take or upload a photo of the package'}
        </p>
        <p className="text-sm text-on-surface-variant/60 mt-1">
          Point at the front of the box where the product name and strength are printed.
        </p>
      </div>

      {scan && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-6">
          <div className="rounded-2xl border border-primary/15 bg-white/60 backdrop-blur-xl p-4 mb-4 flex gap-3">
            <span className="material-symbols-outlined text-primary shrink-0">info</span>
            <p className="text-sm text-on-surface-variant leading-relaxed">{scan.note}</p>
          </div>

          <div className="space-y-2">
            {scan.candidates.map((c) => (
              <button key={c.rxcui} onClick={() => onSelect(c)}
                className="w-full text-left rounded-2xl border border-white/40 bg-white/60 backdrop-blur-2xl p-4 hover:border-primary/30 hover:bg-white/80 transition-all">
                <p className="font-bold text-on-surface">{c.name}</p>
                <p className="text-xs text-on-surface-variant/60 mt-0.5">
                  Read from “{c.matched_text}” · RxCUI {c.rxcui}
                </p>
              </button>
            ))}
          </div>

          {scan.extracted_text && (
            <details className="mt-4">
              <summary className="text-xs font-bold uppercase tracking-wider text-on-surface-variant/60 cursor-pointer">
                Text read from the photo
              </summary>
              <pre className="mt-2 text-xs whitespace-pre-wrap rounded-xl bg-surface-container-low p-3 text-on-surface-variant max-h-48 overflow-auto">
                {scan.extracted_text}
              </pre>
            </details>
          )}
        </motion.div>
      )}
    </>
  );
}

function DoseDialog({ product, onClose, onAdded, setError }) {
  const [units, setUnits] = useState(1);
  const [perDay, setPerDay] = useState(1);
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    setSaving(true);
    try {
      await medicationAPI.add({
        rxcui: product.rxcui,
        display_name: product.name,
        units_per_dose: Number(units),
        doses_per_day: Number(perDay),
        schedule_note: note || undefined,
        entry_source: product.matched_text ? 'ocr' : 'search',
      });
      onAdded();
    } catch (err) {
      setError(err.response?.data?.message || 'Could not add that medication.');
      setSaving(false);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-inverse-surface/30 backdrop-blur-sm"
      onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-3xl border border-white/50 bg-white/90 backdrop-blur-3xl p-6 shadow-2xl"
      >
        <h3 className="font-bold text-lg text-on-surface">How do you take it?</h3>
        <p className="text-sm text-on-surface-variant/70 mt-1 mb-5">{product.name}</p>

        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant/60">
            Units per dose
            <input type="number" min="0.25" step="0.25" value={units}
              onChange={(e) => setUnits(e.target.value)}
              className="mt-1 block w-full rounded-xl border border-outline-variant bg-white px-3 py-2.5 text-base font-normal text-on-surface normal-case tracking-normal" />
          </label>
          <label className="text-xs font-bold uppercase tracking-wider text-on-surface-variant/60">
            Doses per day
            <input type="number" min="0.25" step="0.25" value={perDay}
              onChange={(e) => setPerDay(e.target.value)}
              className="mt-1 block w-full rounded-xl border border-outline-variant bg-white px-3 py-2.5 text-base font-normal text-on-surface normal-case tracking-normal" />
          </label>
        </div>

        <label className="block mt-3 text-xs font-bold uppercase tracking-wider text-on-surface-variant/60">
          When (optional)
          <input value={note} onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. only when needed, at night"
            className="mt-1 block w-full rounded-xl border border-outline-variant bg-white px-3 py-2.5 text-base font-normal text-on-surface normal-case tracking-normal placeholder:text-on-surface-variant/40" />
        </label>

        <p className="mt-4 text-xs text-on-surface-variant/60 leading-relaxed">
          Enter the most you would take on a normal day. The check adds these totals up
          across every product on your list.
        </p>

        <div className="mt-6 flex gap-3">
          <button onClick={submit} disabled={saving}
            className="flex-1 py-3 rounded-2xl bg-gradient-to-r from-primary to-primary-container text-white font-bold shadow-lg shadow-primary/20 disabled:opacity-60">
            {saving ? 'Adding…' : 'Add to my list'}
          </button>
          <button onClick={onClose} className="px-5 py-3 rounded-2xl font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors">
            Cancel
          </button>
        </div>
      </motion.div>
    </div>
  );
}
