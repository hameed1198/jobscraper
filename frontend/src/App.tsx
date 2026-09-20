import { useEffect, useMemo, useState } from "react";
import { Bell, BriefcaseBusiness, ChevronDown, Command, ExternalLink, Sparkles, X } from "lucide-react";
import { JobCard } from "./components/JobCard";
import { LoginPage } from "./components/LoginPage";
import { ProfileDialog } from "./components/ProfileDialog";
import { SearchPanel } from "./components/SearchPanel";
import { searchJobs } from "./lib/jobs";
import type { Job, SearchFilters, User } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const initial: SearchFilters = { query: "Frontend Engineer", company: "", location: "India", mode: "Any", freshness: "Last 24 hours" };
type View = "discover" | "saved" | "match";

export default function App() {
  const [filters, setFilters] = useState(initial);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState<string[]>([]);
  const [sort, setSort] = useState("Best match");
  const [view, setView] = useState<View>("discover");
  const [selected, setSelected] = useState<Job | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const [token, setToken] = useState(() => localStorage.getItem("jobscout_token") ?? "");
  const [user, setUser] = useState<User | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);

  const flash = (message: string) => { setNotice(message); window.setTimeout(() => setNotice(""), 2400); };

  useEffect(() => {
    if (!token) { setCheckingAuth(false); return; }
    let active = true;
    fetch(`${API_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(response => response.ok ? response.json() : Promise.reject(new Error("Session expired")))
      .then((data: { user: User }) => { const savedProfile = localStorage.getItem("jobscout_profile"); if (active) setUser(savedProfile ? { ...data.user, ...JSON.parse(savedProfile) } : data.user); })
      .catch(() => { localStorage.removeItem("jobscout_token"); if (active) { setToken(""); setUser(null); } })
      .finally(() => { if (active) setCheckingAuth(false); });
    return () => { active = false; };
  }, [token]);

  const runSearch = async () => {
    setLoading(true);
    const result = await searchJobs(filters);
    setJobs(result.jobs);
    setLoading(false);
    setView("discover");
    flash(result.warning || `${result.jobs.length} matching roles updated`);
  };

  useEffect(() => { if (user) void runSearch(); }, [user]);

  const shown = view === "saved" ? jobs.filter(job => saved.includes(job.id)) : jobs;
  const sorted = useMemo(() => [...shown].sort((a, b) => sort === "Best match" ? b.match - a.match : 0), [shown, sort]);
  const toggleSave = (id: string) => { const add = !saved.includes(id); setSaved(items => add ? [...items, id] : items.filter(item => item !== id)); flash(add ? "Job saved to your shortlist" : "Job removed from shortlist"); };
  const login = (nextToken: string, nextUser: User) => { const savedProfile = localStorage.getItem("jobscout_profile"); localStorage.setItem("jobscout_token", nextToken); setToken(nextToken); setUser(savedProfile ? { ...nextUser, ...JSON.parse(savedProfile) } : nextUser); flash("Signed in to JobScout"); };
  const updateProfile = (nextUser: User) => { localStorage.setItem("jobscout_profile", JSON.stringify(nextUser)); setUser(nextUser); flash("Profile updated"); };
  const logout = async () => { if (token) await fetch(`${API_URL}/api/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).catch(() => null); localStorage.removeItem("jobscout_token"); setToken(""); setUser(null); setJobs([]); setSaved([]); setProfileOpen(false); setView("discover"); };
  const apply = (job: Job) => { if (!job.url || job.url === "#") { flash("Application link is not available for this role yet"); return; } window.open(job.url, "_blank", "noopener,noreferrer"); };

  if (checkingAuth) return <main className="auth-shell"><div className="auth-loading">Loading JobScout...</div></main>;
  if (!user) return <LoginPage onLogin={login}/>;

  return <main><nav><button className="brand" onClick={() => setView("discover")}><span><BriefcaseBusiness size={20}/></span>Job<span>Scout</span></button><div className="nav-links"><button className={view === "discover" ? "current" : ""} onClick={() => setView("discover")}>Discover</button><button className={view === "saved" ? "current" : ""} onClick={() => setView("saved")}>Saved jobs <b>{saved.length}</b></button><button className={view === "match" ? "current" : ""} onClick={() => setView("match")}>Resume match</button></div><div className="nav-actions"><button aria-label="Notifications" onClick={() => flash("You are all caught up. No new alerts.")}><Bell size={19}/></button><button className="avatar" onClick={() => setProfileOpen(true)}>{user.initials}</button></div></nav>
  {notice && <div className="toast">{notice}</div>}
  <div className="view-transition" key={view}>{view === "match" ? <ResumeMatch onBack={() => setView("discover")}/> : <><div className="hero"><div><p className="overline"><Sparkles size={14}/> YOUR NEXT GREAT ROLE</p><h1>{view === "saved" ? <>Your saved <em>roles.</em></> : <>Find work that <em>fits.</em></>}</h1><p>{view === "saved" ? "Keep track of opportunities you want to revisit." : "Curated opportunities, matched to your skills and how you want to work."}</p></div><div className="hero-stat"><strong>2,480</strong><span>new jobs this week</span></div></div><SearchPanel filters={filters} onChange={setFilters} onSearch={runSearch}/><section className="results"><div className="results-heading"><div><p className="eyebrow">{view === "saved" ? "YOUR SHORTLIST" : "OPPORTUNITIES FOR YOU"}</p><h2>{loading ? "Searching..." : `${sorted.length} roles found`}</h2></div><button className="sort" onClick={() => setSort(sort === "Best match" ? "Newest" : "Best match")}>{sort}<ChevronDown size={16}/></button></div><div className="content"><div className="job-list">{sorted.length ? sorted.map(job => <JobCard key={job.id} job={job} saved={saved.includes(job.id)} onSave={() => toggleSave(job.id)} onView={() => setSelected(job)}/>) : <div className="empty"><h3>{view === "saved" ? "No jobs saved yet" : "No roles found"}</h3><p>{view === "saved" ? "Save an opportunity from Discover to build your shortlist." : "Try a broader role, company, or location search."}</p><button onClick={() => setView("discover")}>Explore jobs</button></div>}</div><aside><div className="match-card"><div className="mini-icon"><Command size={18}/></div><p className="eyebrow">RESUME MATCH</p><h3>See how you stack up</h3><p>Paste your resume and get a practical keyword match score.</p><button onClick={() => setView("match")}>Analyze my resume</button></div><div className="tip"><span>*</span><div><strong>Smart search tip</strong><p>Use specific skills like "React + FastAPI" for more relevant results.</p></div></div></aside></div></section></>}</div>
  {selected && <JobDialog job={selected} saved={saved.includes(selected.id)} onApply={() => apply(selected)} onSave={() => toggleSave(selected.id)} onClose={() => setSelected(null)}/>} {profileOpen && <ProfileDialog user={user} onUpdate={updateProfile} onLogout={logout} onClose={() => setProfileOpen(false)}/>}</main>;
}

function JobDialog({ job, saved, onApply, onSave, onClose }: { job: Job; saved: boolean; onApply: () => void; onSave: () => void; onClose: () => void }) { return <div className="overlay" onMouseDown={onClose}><div className="dialog" onMouseDown={event => event.stopPropagation()}><button className="close" onClick={onClose}><X size={20}/></button><p className="eyebrow">{job.source} · {job.posted}</p><h2>{job.title}</h2><p className="dialog-company">{job.company} · {job.location} · {job.mode}</p><p>{job.description}</p><div className="tags">{job.tags.map(tag => <span key={tag}>{tag}</span>)}</div><div className="dialog-actions"><button className="primary" onClick={onApply}>Apply now <ExternalLink size={15}/></button><button className="secondary" onClick={onSave}>{saved ? "Remove from saved" : "Save this role"}</button></div></div></div>; }
function ResumeMatch({ onBack }: { onBack: () => void }) { const [resume, setResume] = useState(""); const [description, setDescription] = useState(""); const [result, setResult] = useState<{score:number; matched_keywords:string[]; missing_keywords:string[]} | null>(null); const [loading, setLoading] = useState(false); const analyze = async () => { if (!resume.trim() || !description.trim()) return; setLoading(true); try { const response = await fetch(`${API_URL}/api/match`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({resume_text:resume, job_description:description})}); setResult(await response.json()); } finally { setLoading(false); } }; return <section className="match-page page-surface"><button className="back" onClick={onBack}>Back to jobs</button><p className="overline"><Sparkles size={14}/> RESUME MATCH</p><h1>Make every application <em>count.</em></h1><p>Paste a resume and a job description to see your keyword overlap.</p><div className="match-form"><textarea value={resume} onChange={event => setResume(event.target.value)} placeholder="Paste your resume text..."/><textarea value={description} onChange={event => setDescription(event.target.value)} placeholder="Paste the job description..."/><button className="primary" disabled={!resume.trim() || !description.trim() || loading} onClick={analyze}>{loading ? "Analyzing..." : "Analyze match"}</button></div>{result && <div className="match-result"><strong>{result.score}% match</strong><p><b>Matched:</b> {result.matched_keywords.join(", ") || "No overlapping keywords yet"}</p><p><b>Consider adding:</b> {result.missing_keywords.slice(0,8).join(", ") || "Great coverage"}</p></div>}</section>; }