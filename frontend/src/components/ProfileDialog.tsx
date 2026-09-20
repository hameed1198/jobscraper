import { LogOut, Plus, Save, UserRound, X } from "lucide-react";
import { useState } from "react";
import type { NoticePeriod, ProfileCompany, User } from "../types";

const noticeOptions: { value: NoticePeriod; label: string }[] = [
  { value: "30", label: "30 days" },
  { value: "60", label: "60 days" },
  { value: "90", label: "90 days" },
  { value: "serving", label: "Serving notice" }
];

function splitName(user: User) {
  const parts = user.name.trim().split(/\s+/);
  return { firstName: user.firstName || parts[0] || "", lastName: user.lastName || parts.slice(1).join(" ") || "" };
}

function initials(firstName: string, lastName: string) {
  return `${firstName[0] || ""}${lastName[0] || ""}`.toUpperCase() || "HK";
}

function blankCompany(): ProfileCompany {
  return { id: crypto.randomUUID(), name: "", startDate: "", endDate: "", current: true };
}

export function ProfileDialog({ user, onUpdate, onLogout, onClose }: { user: User; onUpdate: (user: User) => void; onLogout: () => void; onClose: () => void }) {
  const [editing, setEditing] = useState(false);
  const nameParts = splitName(user);
  const [firstName, setFirstName] = useState(nameParts.firstName);
  const [lastName, setLastName] = useState(nameParts.lastName);
  const [role, setRole] = useState(user.role || "");
  const [cctc, setCctc] = useState(user.cctc || "");
  const [ectc, setEctc] = useState(user.ectc || "");
  const [companies, setCompanies] = useState<ProfileCompany[]>(user.companies?.length ? user.companies : [blankCompany()]);
  const [noticePeriod, setNoticePeriod] = useState<NoticePeriod>(user.noticePeriod || "30");
  const [lastWorkingDate, setLastWorkingDate] = useState(user.lastWorkingDate || "");

  const updateCompany = (id: string, patch: Partial<ProfileCompany>) => setCompanies(items => items.map(company => company.id === id ? { ...company, ...patch, endDate: patch.current ? "" : company.endDate } : company));
  const removeCompany = (id: string) => setCompanies(items => items.length === 1 ? items : items.filter(company => company.id !== id));
  const save = () => {
    const trimmedFirstName = firstName.trim();
    const trimmedLastName = lastName.trim();
    onUpdate({
      ...user,
      firstName: trimmedFirstName,
      lastName: trimmedLastName,
      name: [trimmedFirstName, trimmedLastName].filter(Boolean).join(" ") || user.name,
      initials: initials(trimmedFirstName, trimmedLastName),
      role: role.trim(),
      cctc: cctc.trim(),
      ectc: ectc.trim(),
      companies: companies.filter(company => company.name.trim()).map(company => ({ ...company, name: company.name.trim() })),
      noticePeriod,
      lastWorkingDate: noticePeriod === "serving" ? lastWorkingDate : ""
    });
    setEditing(false);
  };

  return <div className="overlay" onMouseDown={onClose}><div className={`dialog profile profile-dialog ${editing ? "profile-editing" : ""}`} onMouseDown={event => event.stopPropagation()}><button className="close" onClick={onClose}><X size={20}/></button><div className="profile-avatar">{user.initials}</div><h2>{user.name}</h2><p>{user.email}</p>{!editing ? <><div className="profile-summary"><span><UserRound size={15}/>{user.role || "Add your target role"}</span><span>{user.noticePeriod === "serving" ? `Serving notice${user.lastWorkingDate ? ` until ${user.lastWorkingDate}` : ""}` : `${user.noticePeriod || "30"} days notice`}</span></div><div className="profile-actions"><button className="primary" onClick={() => setEditing(true)}>Update profile</button><button className="secondary" onClick={onClose}>Close</button><button className="logout-button" onClick={onLogout}><LogOut size={15}/> Sign out</button></div></> : <form className="profile-form" onSubmit={event => { event.preventDefault(); save(); }}><div className="form-grid"><label><span>First name</span><input value={firstName} onChange={event => setFirstName(event.target.value)}/></label><label><span>Last name</span><input value={lastName} onChange={event => setLastName(event.target.value)}/></label><label><span>Role</span><input value={role} onChange={event => setRole(event.target.value)} placeholder="Data Engineer"/></label><label><span>CCTC</span><input value={cctc} onChange={event => setCctc(event.target.value)} placeholder="Current CTC"/></label><label><span>ECTC</span><input value={ectc} onChange={event => setEctc(event.target.value)} placeholder="Expected CTC"/></label><label><span>Notice period</span><select value={noticePeriod} onChange={event => setNoticePeriod(event.target.value as NoticePeriod)}>{noticeOptions.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>{noticePeriod === "serving" && <label><span>Last working date</span><input type="date" value={lastWorkingDate} onChange={event => setLastWorkingDate(event.target.value)}/></label>}</div><div className="company-editor"><div className="company-editor-head"><span>Current company</span><button type="button" onClick={() => setCompanies(items => [...items, blankCompany()])}><Plus size={14}/> Add company</button></div>{companies.map(company => <div className="company-row" key={company.id}><input value={company.name} onChange={event => updateCompany(company.id, { name: event.target.value })} placeholder="Company name"/><input type="date" value={company.startDate} onChange={event => updateCompany(company.id, { startDate: event.target.value })}/><label className="current-check"><input type="checkbox" checked={company.current} onChange={event => updateCompany(company.id, { current: event.target.checked })}/> Current</label><input type="date" value={company.endDate} disabled={company.current} onChange={event => updateCompany(company.id, { endDate: event.target.value })}/><button type="button" className="remove-company" onClick={() => removeCompany(company.id)}>Remove</button></div>)}</div><div className="profile-actions"><button className="primary" type="submit"><Save size={15}/> Save profile</button><button className="secondary" type="button" onClick={() => setEditing(false)}>Cancel</button></div></form>}</div></div>;
}