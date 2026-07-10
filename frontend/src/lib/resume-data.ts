export type Chapter = {
  id: string;
  kind: "hero" | "chapter" | "outro";
  building: string;
  logo?: "rit" | "amd" | "siemens";
  dates?: string;
  title: string;
  subtitle?: string;
  bullets?: string[];
  links?: { label: string; href: string }[];
  /** camera dolly position/target along the street, in world units */
  cameraX: number;
};

export const CHAPTERS: Chapter[] = [
  {
    id: "hero",
    kind: "hero",
    building: "street-overview",
    title: "Chinmay Rozekar",
    subtitle:
      "I build automation and agentic infrastructure that accelerates validation, debugging, and quality engineering for large, complex platforms.",
    cameraX: -2,
  },
  {
    id: "rit",
    kind: "chapter",
    building: "rit-hall",
    logo: "rit",
    dates: "2017 – 2020",
    title: "Rochester Institute of Technology",
    subtitle: "MS Electrical Engineering — Graduate Researcher",
    bullets: [
      "Developed a process flow for thin-film IC fabrication, covering multiple process steps end to end.",
      "Designed and simulated NMOS devices to determine sub-threshold voltages and model leakage current.",
      "Fabricated a thermally actuated four-legged MEMS silicon micro-robot (SolidWorks + COMSOL Multiphysics FEA).",
    ],
    cameraX: 6,
  },
  {
    id: "amd",
    kind: "chapter",
    building: "factory",
    logo: "amd",
    dates: "2019 – 2024",
    title: "AMD",
    subtitle: "ESD Co-op → Product Development Engineer, System-Level Test",
    bullets: [
      "Raised silicon yield from 42% to 85% by debugging BIOS/voltage/frequency/thermal parameters across CPU and memory subsystems.",
      "Built a Python + Selenium WorkOrder Automator, cutting manual work-order filing by 90%.",
      "Led cross-functional debug across diagnostics, BIOS, and validation teams; built RMA/JTAG debug workflows and in-house server-farm test infrastructure.",
      "Earlier, as an ESD co-op: automated Human Body Model (HBM) test programs (−90% engineering effort) and rebuilt a 20-year-old robotic GUI in Python (−95% manual interaction time).",
    ],
    cameraX: 18,
  },
  {
    id: "siemens",
    kind: "chapter",
    building: "tower",
    logo: "siemens",
    dates: "2024 – 2025",
    title: "Siemens EDA",
    subtitle: "Software QA Engineer, Calibre PERC",
    bullets: [
      "Cut regression setup/debug time 20% by automating testcase checkout, config validation, and log parsing in Python/Bash/Tcl.",
      "Cut nightly regression failures 15% with pre-run validation checks for environments, configs, and execution guards.",
      "Validated SVRF/TVF rules across single-threaded, multi-threaded, and distributed (MTFlex) modes for Calibre PERC releases.",
    ],
    cameraX: 30,
  },
  {
    id: "ai-agents",
    kind: "chapter",
    building: "signal-tower",
    dates: "2025 – present",
    title: "AI & Agentic Systems",
    subtitle: "triagent · punjab-pulse · applied research",
    bullets: [
      "triagent — a local, sovereign agentic RAG log-triage system (Drain3 + FAISS + Ollama) for 80GB+ semiconductor/network logs.",
      "punjab-pulse — a live news aggregator (Next.js/FastAPI/Postgres) deployed on Vercel + Render + Neon.",
      "Published research on high-throughput log parsing architectures and AI-integrated open-source EDA toolchains.",
    ],
    links: [
      { label: "triagent →", href: "https://github.com/chinmayrozekar/triagent" },
      { label: "punjab-pulse →", href: "https://github.com/chinmayrozekar/punjab-pulse" },
    ],
    cameraX: 42,
  },
  {
    id: "openusd",
    kind: "chapter",
    building: "construction",
    dates: "now",
    title: "Learning OpenUSD",
    subtitle: "Why this site exists",
    bullets: [
      "This entire site — every block, every building — is authored in OpenUSD with Python (pxr), then exported through a hand-built USD→glTF pipeline for real-time web delivery.",
      "Built in pursuit of NVIDIA's Omniverse platform: agentic test infrastructure applied to a complex, composition-heavy SDK.",
      "Still under construction, on purpose — this chapter updates as the work continues.",
    ],
    cameraX: 54,
  },
  {
    id: "contact",
    kind: "outro",
    building: "signpost",
    title: "Let's talk",
    subtitle: "chinmay.rozekar.careers@gmail.com",
    links: [
      { label: "GitHub →", href: "https://github.com/chinmayrozekar" },
      { label: "LinkedIn →", href: "https://linkedin.com/in/chinmayrozekar" },
    ],
    cameraX: 64,
  },
];
