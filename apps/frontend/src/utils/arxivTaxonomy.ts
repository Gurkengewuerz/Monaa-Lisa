// arXiv "taxonomy" based on https://arxiv.org/category_taxonomy
// DISCLAIMER: Ripped the categories manually from the arXiv page, used AI though to generate this mundate ts file. - Nick, February 09 2026

export interface Category {
  name: string;
  subcategories: Record<string, string>;
}

export const ARXIV_TAXONOMY: Record<string, Category> = {
  "Computer Science": {
    name: "Computer Science",
    subcategories: {
      "cs.AI": "Artificial Intelligence",
      "cs.AR": "Hardware Architecture",
      "cs.CC": "Computational Complexity",
      "cs.CE": "Computational Engineering, Finance, and Science",
      "cs.CG": "Computational Geometry",
      "cs.CL": "Computation and Language",
      "cs.CR": "Cryptography and Security",
      "cs.CV": "Computer Vision and Pattern Recognition",
      "cs.CY": "Computers and Society",
      "cs.DB": "Databases",
      "cs.DC": "Distributed, Parallel, and Cluster Computing",
      "cs.DL": "Digital Libraries",
      "cs.DM": "Discrete Mathematics",
      "cs.DS": "Data Structures and Algorithms",
      "cs.ET": "Emerging Technologies",
      "cs.FL": "Formal Languages and Automata Theory",
      "cs.GL": "General Literature",
      "cs.GR": "Graphics",
      "cs.GT": "Computer Science and Game Theory",
      "cs.HC": "Human-Computer Interaction",
      "cs.IR": "Information Retrieval",
      "cs.IT": "Information Theory",
      "cs.LG": "Machine Learning",
      "cs.LO": "Logic in Computer Science",
      "cs.MA": "Multiagent Systems",
      "cs.MM": "Multimedia",
      "cs.MS": "Mathematical Software",
      "cs.NA": "Numerical Analysis",
      "cs.NE": "Neural and Evolutionary Computing",
      "cs.NI": "Networking and Internet Architecture",
      "cs.OH": "Other Computer Science",
      "cs.OS": "Operating Systems",
      "cs.PF": "Performance",
      "cs.PL": "Programming Languages",
      "cs.RO": "Robotics",
      "cs.SC": "Symbolic Computation",
      "cs.SD": "Sound",
      "cs.SE": "Software Engineering",
      "cs.SI": "Social and Information Networks",
      "cs.SY": "Systems and Control",
    },
  },
  Physics: {
    name: "Physics",
    subcategories: {
      // Astrophysics
      "astro-ph.CO": "Cosmology and Nongalactic Astrophysics",
      "astro-ph.EP": "Earth and Planetary Astrophysics",
      "astro-ph.GA": "Astrophysics of Galaxies",
      "astro-ph.HE": "High Energy Astrophysical Phenomena",
      "astro-ph.IM": "Instrumentation and Methods for Astrophysics",
      "astro-ph.SR": "Solar and Stellar Astrophysics",
      // Condensed Matter
      "cond-mat.dis-nn": "Disordered Systems and Neural Networks",
      "cond-mat.mes-hall": "Mesoscale and Nanoscale Physics",
      "cond-mat.mtrl-sci": "Materials Science",
      "cond-mat.other": "Other Condensed Matter",
      "cond-mat.quant-gas": "Quantum Gases",
      "cond-mat.soft": "Soft Condensed Matter",
      "cond-mat.stat-mech": "Statistical Mechanics",
      "cond-mat.str-el": "Strongly Correlated Electrons",
      "cond-mat.supr-con": "Superconductivity",
      // Nonlinear Sciences
      "nlin.AO": "Adaptation and Self-Organizing Systems",
      "nlin.CD": "Chaotic Dynamics",
      "nlin.CG": "Cellular Automata and Lattice Gases",
      "nlin.PS": "Pattern Formation and Solitons",
      "nlin.SI": "Exactly Solvable and Integrable Systems",
      // Physics (General)
      "physics.acc-ph": "Accelerator Physics",
      "physics.ao-ph": "Atmospheric and Oceanic Physics",
      "physics.app-ph": "Applied Physics",
      "physics.atm-clus": "Atomic and Molecular Clusters",
      "physics.atom-ph": "Atomic Physics",
      "physics.bio-ph": "Biological Physics",
      "physics.chem-ph": "Chemical Physics",
      "physics.class-ph": "Classical Physics",
      "physics.comp-ph": "Computational Physics",
      "physics.data-an": "Data Analysis, Statistics and Probability",
      "physics.ed-ph": "Physics Education",
      "physics.flu-dyn": "Fluid Dynamics",
      "physics.gen-ph": "General Physics",
      "physics.geo-ph": "Geophysics",
      "physics.hist-ph": "History and Philosophy of Physics",
      "physics.ins-det": "Instrumentation and Detectors",
      "physics.med-ph": "Medical Physics",
      "physics.optics": "Optics",
      "physics.soc-ph": "Physics and Society",
      "physics.space-ph": "Space Physics",
      // Other Physics Archives
      "gr-qc": "General Relativity and Quantum Cosmology",
      "hep-ex": "High Energy Physics - Experiment",
      "hep-lat": "High Energy Physics - Lattice",
      "hep-ph": "High Energy Physics - Phenomenology",
      "hep-th": "High Energy Physics - Theory",
      "math-ph": "Mathematical Physics",
      "nucl-ex": "Nuclear Experiment",
      "nucl-th": "Nuclear Theory",
      "quant-ph": "Quantum Physics",
    },
  },
  Mathematics: {
    name: "Mathematics",
    subcategories: {
      "math.AC": "Commutative Algebra",
      "math.AG": "Algebraic Geometry",
      "math.AP": "Analysis of PDEs",
      "math.AT": "Algebraic Topology",
      "math.CA": "Classical Analysis and ODEs",
      "math.CO": "Combinatorics",
      "math.CT": "Category Theory",
      "math.CV": "Complex Variables",
      "math.DG": "Differential Geometry",
      "math.DS": "Dynamical Systems",
      "math.FA": "Functional Analysis",
      "math.GM": "General Mathematics",
      "math.GN": "General Topology",
      "math.GR": "Group Theory",
      "math.GT": "Geometric Topology",
      "math.HO": "History and Overview",
      "math.IT": "Information Theory",
      "math.KT": "K-Theory and Homology",
      "math.LO": "Logic",
      "math.MG": "Metric Geometry",
      "math.MP": "Mathematical Physics",
      "math.NA": "Numerical Analysis",
      "math.NT": "Number Theory",
      "math.OA": "Operator Algebras",
      "math.OC": "Optimization and Control",
      "math.PR": "Probability",
      "math.QA": "Quantum Algebra",
      "math.RA": "Rings and Algebras",
      "math.RT": "Representation Theory",
      "math.SG": "Symplectic Geometry",
      "math.SP": "Spectral Theory",
      "math.ST": "Statistics Theory",
    },
  },
  Economics: {
    name: "Economics",
    subcategories: {
      "econ.EM": "Econometrics",
      "econ.GN": "General Economics",
      "econ.TH": "Theoretical Economics",
    },
  },
  "Electrical Engineering": {
    name: "Electrical Engineering and Systems Science",
    subcategories: {
      "eess.AS": "Audio and Speech Processing",
      "eess.IV": "Image and Video Processing",
      "eess.SP": "Signal Processing",
      "eess.SY": "Systems and Control",
    },
  },
  "Quantitative Biology": {
    name: "Quantitative Biology",
    subcategories: {
      "q-bio.BM": "Biomolecules",
      "q-bio.CB": "Cell Behavior",
      "q-bio.GN": "Genomics",
      "q-bio.MN": "Molecular Networks",
      "q-bio.NC": "Neurons and Cognition",
      "q-bio.OT": "Other Quantitative Biology",
      "q-bio.PE": "Populations and Evolution",
      "q-bio.QM": "Quantitative Methods",
      "q-bio.SC": "Subcellular Processes",
      "q-bio.TO": "Tissues and Organs",
    },
  },
  "Quantitative Finance": {
    name: "Quantitative Finance",
    subcategories: {
      "q-fin.CP": "Computational Finance",
      "q-fin.EC": "Economics",
      "q-fin.GN": "General Finance",
      "q-fin.MF": "Mathematical Finance",
      "q-fin.PM": "Portfolio Management",
      "q-fin.PR": "Pricing of Securities",
      "q-fin.RM": "Risk Management",
      "q-fin.ST": "Statistical Finance",
      "q-fin.TR": "Trading and Market Microstructure",
    },
  },
  Statistics: {
    name: "Statistics",
    subcategories: {
      "stat.AP": "Applications",
      "stat.CO": "Computation",
      "stat.ME": "Methodology",
      "stat.ML": "Machine Learning",
      "stat.OT": "Other Statistics",
      "stat.TH": "Statistics Theory",
    },
  },
};

/*
this helper list allows us to quickly determine the main category (e.g. "Computer Science") for a given subcategory id (e.g. "cs.AI").
We know the abbreviation (e.g. "cs.AI") and want to immediately know which main categoryit belongs to
Without this list, we would have to browse through all categories everytime to find it
With this list, we look in one place
  
e.g. cs.AI -> to Computer Science
*/
export const SUBCATEGORY_TO_TOPLEVEL: Record<string, string> = {};

/**
 * another helper list to quickly get the full name of a subcategory based on its symbol.
 * we use this to translate the symbol (e.g. "cs.AI") into a human-readable name (e.g. "Artificial Intelligence") when we display it in the frontend.
 *
 * e.g. cs.AI -> to Artificial Intelligence
 */
export const SUBCATEGORY_NAMES: Record<string, string> = {};

/*
this block runs once when the module is loaded. It goes through the big main list (ARXIV_TAXONOMY) and fills the two helper lists above.
its a bit of upfront work, but it makes the lookups super fast later on when we need to determine the main category or the full name of a subcategory
*/
Object.entries(ARXIV_TAXONOMY).forEach(([topLevel, data]) => {
  Object.entries(data.subcategories).forEach(([subId, subName]) => {
    SUBCATEGORY_TO_TOPLEVEL[subId] = topLevel;
    SUBCATEGORY_NAMES[subId] = subName;
  });
});

/**
 * find the main category for a given subcategory id
 *
 * Giving this function a subcategory id (e.g. "cs.AI")
 * it returns the name of the main category (e.g. "Computer Science").
 * we use this function to quickly determine the main category of a paper based on its subcategory, without having to loop through the entire taxonomy each time.
 * @param subcategoryId - The symbol e.g. "cs.AI"
 * @returns The name of the main category or 'other' if unknown
 */
export function getTopLevelCategory(subcategoryId: string): string {
  return SUBCATEGORY_TO_TOPLEVEL[subcategoryId] || "Other";
}

/**
 * translate a symbol into the full name of the subcategory
 * @param subcategoryId - The symbol e.g.. "cs.AI"
 * @returns Full name, e.g. "Artificial Intelligence".
 *          If the symbol isnot known, it simply returns the symbol itself for safety
 */
export function getSubcategoryName(subcategoryId: string): string {
  return SUBCATEGORY_NAMES[subcategoryId] || subcategoryId;
}
