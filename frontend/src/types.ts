export type WorkMode = "Remote" | "Hybrid" | "On-site";
export type Job = { id: string; title: string; company: string; location: string; mode: WorkMode; posted: string; salary: string; match: number; tags: string[]; source: string; description: string; url: string };
export type SearchFilters = { query: string; company: string; location: string; mode: WorkMode | "Any"; freshness: string };
export type SearchResult = { jobs: Job[]; warning?: string };
export type ProfileCompany = { id: string; name: string; startDate: string; endDate: string; current: boolean };
export type NoticePeriod = "30" | "60" | "90" | "serving";
export type User = { name: string; email: string; initials: string; firstName?: string; lastName?: string; role?: string; cctc?: string; ectc?: string; companies?: ProfileCompany[]; noticePeriod?: NoticePeriod; lastWorkingDate?: string };
