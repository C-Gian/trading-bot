import { KeyboardEvent, useEffect, useId, useRef, useState } from 'react';
import { ResearchRunnerCandidate } from './api';

type Props = {
  candidates: ResearchRunnerCandidate[];
  value: string;
  disabled: boolean;
  onChange: (candidateId: string) => void;
};

export function ResearchCandidatePicker({ candidates, value, disabled, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const selectedIndex = Math.max(0, candidates.findIndex(item => item.candidate_id === value));
  const [activeIndex, setActiveIndex] = useState(selectedIndex);
  const root = useRef<HTMLDivElement>(null);
  const listboxId = useId();
  const labelId = useId();
  const selected = candidates[selectedIndex];

  useEffect(() => setActiveIndex(selectedIndex), [selectedIndex]);
  useEffect(() => {
    const close = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', close);
    return () => document.removeEventListener('pointerdown', close);
  }, []);

  const choose = (index: number) => {
    const candidate = candidates[index];
    if (!candidate) return;
    onChange(candidate.candidate_id);
    setActiveIndex(index);
    setOpen(false);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (disabled || candidates.length === 0) return;
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const direction = event.key === 'ArrowDown' ? 1 : -1;
      const origin = open ? activeIndex : selectedIndex;
      setActiveIndex((origin + direction + candidates.length) % candidates.length);
      setOpen(true);
    } else if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault();
      setActiveIndex(event.key === 'Home' ? 0 : candidates.length - 1);
      setOpen(true);
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (open) choose(activeIndex);
      else setOpen(true);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      setOpen(false);
      setActiveIndex(selectedIndex);
    } else if (event.key === 'Tab') {
      setOpen(false);
    }
  };

  return (
    <div className="research-picker" ref={root}>
      <span id={labelId}>Candidato scientifico</span>
      <button
        type="button"
        className="research-combobox"
        role="combobox"
        aria-labelledby={labelId}
        aria-controls={listboxId}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-activedescendant={open ? `${listboxId}-${activeIndex}` : undefined}
        disabled={disabled}
        onClick={() => setOpen(current => !current)}
        onKeyDown={onKeyDown}
      >
        <span>{selected?.display_name ?? 'Nessun candidato'}</span>
        <span className="research-combobox-chevron" aria-hidden="true">⌄</span>
      </button>
      {open && (
        <div className="research-listbox" id={listboxId} role="listbox" aria-labelledby={labelId}>
          {candidates.map((item, index) => (
            <div
              id={`${listboxId}-${index}`}
              key={item.candidate_id}
              className="research-option"
              role="option"
              aria-selected={item.candidate_id === value}
              data-active={index === activeIndex}
              onMouseDown={event => event.preventDefault()}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => choose(index)}
            >
              <span>{item.display_name}</span>
              {item.candidate_id === value && <span aria-hidden="true">✓</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
