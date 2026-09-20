import type { Job, SearchFilters, SearchResult } from "../types";

const demo: Job[] = [
  { id: "1", title: "Senior Frontend Engineer", company: "Vercel", location: "Remote · India", mode: "Remote", posted: "2h ago", salary: "₹32L - ₹48L", match: 94, tags: ["React", "TypeScript", "Next.js"], source: "Company careers", description: "Build delightful developer tools and high-performance web experiences.", url: "https://vercel.com/careers" },
  { id: "2", title: "Full Stack Developer", company: "Razorpay", location: "Bengaluru, India", mode: "Hybrid", posted: "5h ago", salary: "₹20L - ₹35L", match: 88, tags: ["React", "Python", "FastAPI"], source: "Company careers", description: "Create reliable products used by millions of businesses every day.", url: "https://razorpay.com/jobs/" },
  { id: "3", title: "Software Engineer, Web", company: "Postman", location: "Remote · India", mode: "Remote", posted: "1d ago", salary: "₹24L - ₹40L", match: 82, tags: ["React", "Node.js", "Design systems"], source: "Company careers", description: "Shape collaboration tools for the global API-first community.", url: "https://www.postman.com/company/careers/" },
  { id: "4", title: "Data Engineer", company: "Atlassian", location: "Remote · India", mode: "Remote", posted: "6h ago", salary: "₹28L - ₹44L", match: 91, tags: ["Python", "SQL", "Spark", "Airflow"], source: "Company careers", description: "Build reliable data pipelines, warehouse models, and analytics-ready datasets for product and business teams.", url: "https://www.atlassian.com/company/careers" },
  { id: "5", title: "Senior Data Engineer", company: "Stripe", location: "Bengaluru, India", mode: "Hybrid", posted: "1d ago", salary: "₹34L - ₹55L", match: 89, tags: ["Python", "ETL", "Kafka", "Snowflake"], source: "Company careers", description: "Design scalable data infrastructure, streaming pipelines, and governed datasets for financial product insights.", url: "https://stripe.com/jobs" }
];

export async function searchJobs(filters: SearchFilters): Promise<SearchResult> {
  try {
    const response = await fetch(`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/jobs/search`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(filters) });
    if (!response.ok) throw new Error("API unavailable");
    const data = await response.json() as SearchResult | Job[];
    return Array.isArray(data) ? { jobs: data } : data;
  } catch {
    const queryWords = filters.query.toLowerCase().split(/\W+/).filter(Boolean);
    const filtered = demo.filter(job => {
      const haystack = [job.title, job.company, job.description, ...job.tags].join(" ").toLowerCase();
      return (filters.mode === "Any" || job.mode === filters.mode) && (!queryWords.length || queryWords.every(word => haystack.includes(word)));
    });
    return { jobs: filtered, warning: "Backend search is unavailable. Showing curated fallback roles." };
  }
}
