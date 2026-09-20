import { Building2, MapPin, Search, SlidersHorizontal } from "lucide-react";
import type { SearchFilters, WorkMode } from "../types";

type Props = { filters: SearchFilters; onChange: (filters: SearchFilters) => void; onSearch: () => void };
const modes: (WorkMode | "Any")[] = ["Any", "Remote", "Hybrid", "On-site"];
export function SearchPanel({ filters, onChange, onSearch }: Props) {
  const set = (field: keyof SearchFilters, value: string) => onChange({ ...filters, [field]: value });
  return <section className="search-panel">
    <div className="query-input"><Search size={20}/><input value={filters.query} onChange={e => set("query", e.target.value)} placeholder="Role, skill, or keyword" /></div>
    <div className="company-input"><Building2 size={20}/><input value={filters.company} onChange={e => set("company", e.target.value)} placeholder="Company for Workday" /></div>
    <div className="location-input"><MapPin size={20}/><input value={filters.location} onChange={e => set("location", e.target.value)} placeholder="Location" /></div>
    <select aria-label="Freshness" value={filters.freshness} onChange={e => set("freshness", e.target.value)}><option>Last 24 hours</option><option>Last 3 days</option><option>Last 7 days</option><option>Any time</option></select>
    <button className="search-button" onClick={onSearch}>Find jobs <Search size={18}/></button>
    <div className="mode-row"><SlidersHorizontal size={16}/>{modes.map(mode => <button key={mode} className={`filter-pill ${filters.mode === mode ? "active" : ""}`} onClick={() => set("mode", mode)}>{mode}</button>)}</div>
  </section>;
}
