from .database import get_connection


def seed_sections():
    conn = get_connection()
    cursor = conn.cursor()

    main_sections = [
        ("🧪 الكيمياء العضوية", "Organic Chemistry"),
        ("⚗️ الكيمياء اللاعضوية", "Inorganic Chemistry"),
        ("🔬 الكيمياء التحليلية", "Analytical Chemistry"),
        ("⚡ الكيمياء الفيزيائية", "Physical Chemistry"),
        ("🧬 الكيمياء الحياتية", "Biochemistry"),
        ("🏭 الكيمياء الصناعية", "Industrial Chemistry"),
        ("🏥 الكيمياء السريرية", "Clinical Chemistry"),
    ]

    for i, (ar, en) in enumerate(main_sections):
        cursor.execute(
            "INSERT OR IGNORE INTO sections (name_ar, name_en, parent_id, sort_order) VALUES (?, ?, NULL, ?)",
            (ar, en, i),
        )

    conn.commit()

    cursor.execute("SELECT id, name_en FROM sections WHERE parent_id IS NULL")
    main_ids = {row["name_en"]: row["id"] for row in cursor.fetchall()}

    subs = {
        "Organic Chemistry": [
            ("الكيمياء العضوية العامة", "General Organic Chemistry"),
            ("التفاعلات العضوية وآلياتها", "Organic Reactions & Mechanisms"),
            ("التخليق العضوي", "Organic Synthesis"),
            ("الكيمياء العضوية الفلزية", "Organometallic Chemistry"),
            ("الكيمياء العضوية الحلقية", "Heterocyclic Chemistry"),
            ("المنتجات الطبيعية", "Natural Products"),
            ("الكيمياء الدوائية", "Medicinal Chemistry"),
            ("البوليمرات", "Polymers"),
        ],
        "Inorganic Chemistry": [
            ("الكيمياء اللاعضوية العامة", "General Inorganic Chemistry"),
            ("كيمياء العناصر الانتقالية", "Transition Metal Chemistry"),
            ("كيمياء التنسيق", "Coordination Chemistry"),
            ("كيمياء المجموعات الرئيسية", "Main Group Chemistry"),
            ("الكيمياء اللاعضوية الصلبة", "Solid State Inorganic Chemistry"),
            ("المواد النانوية اللاعضوية", "Inorganic Nanomaterials"),
        ],
        "Analytical Chemistry": [
            ("الكيمياء التحليلية العامة", "General Analytical Chemistry"),
            ("الكروماتوغرافيا", "Chromatography"),
            ("المطيافية", "Spectroscopy"),
            ("الطرق الكهربائية", "Electroanalytical Methods"),
            ("الكيمياء التحليلية الحسية", "Sensory Analytical Chemistry"),
            ("تحليل الأغذية", "Food Analysis"),
            ("التحليل البيئي", "Environmental Analysis"),
        ],
        "Physical Chemistry": [
            ("الثرموداينمك الكيميائي", "Chemical Thermodynamics"),
            ("الكيمياء الكهربائية", "Electrochemistry"),
            ("كيمياء الكم", "Quantum Chemistry"),
            ("الحركية الكيميائية", "Chemical Kinetics"),
            ("الكيمياء الضوئية", "Photochemistry"),
            ("كيمياء السطوح", "Surface Chemistry"),
            ("كيمياء المحاليل", "Solution Chemistry"),
            ("ميكانيكا الموائع", "Fluid Mechanics"),
        ],
        "Biochemistry": [
            ("الكيمياء الحيوية العامة", "General Biochemistry"),
            ("الإنزيمات", "Enzymology"),
            ("الأيض", "Metabolism"),
            ("البيولوجيا الجزيئية", "Molecular Biology"),
            ("الكيمياء الحيوية السريرية", "Clinical Biochemistry"),
            ("الوراثة الجزيئية", "Molecular Genetics"),
            ("البروتيوميات", "Proteomics"),
        ],
        "Industrial Chemistry": [
            ("الكيمياء الصناعية العامة", "General Industrial Chemistry"),
            ("البتروكيمياويات", "Petrochemicals"),
            ("الهندسة الكيميائية", "Chemical Engineering"),
            ("تقنيات الفصل", "Separation Technologies"),
            ("الكيمياء الخضراء", "Green Chemistry"),
            ("المحفزات الصناعية", "Industrial Catalysis"),
            ("معالجة المياه", "Water Treatment"),
        ],
        "Clinical Chemistry": [
            ("الكيمياء السريرية العامة", "General Clinical Chemistry"),
            ("تحليل الدم", "Hematology Analysis"),
            ("تحليل البول", "Urinalysis"),
            ("الهرمونات", "Hormones"),
            ("السموم السريرية", "Clinical Toxicology"),
            ("المؤشرات الحيوية", "Biomarkers"),
        ],
    }

    for main_en, sublist in subs.items():
        main_id = main_ids.get(main_en)
        if main_id is None:
            continue
        for j, (ar, en) in enumerate(sublist):
            cursor.execute(
                "INSERT OR IGNORE INTO sections (name_ar, name_en, parent_id, sort_order) VALUES (?, ?, ?, ?)",
                (ar, en, main_id, j),
            )

    conn.commit()
    conn.close()


SECTION_KEYWORDS = {
    "General Organic Chemistry": "organic chemistry fundamentals",
    "Organic Reactions & Mechanisms": "organic reaction mechanism",
    "Organic Synthesis": "organic synthesis methodology",
    "Organometallic Chemistry": "organometallic chemistry",
    "Heterocyclic Chemistry": "heterocyclic chemistry",
    "Natural Products": "natural products chemistry",
    "Medicinal Chemistry": "medicinal chemistry drug discovery",
    "Polymers": "polymer chemistry",
    "General Inorganic Chemistry": "inorganic chemistry",
    "Transition Metal Chemistry": "transition metal chemistry",
    "Coordination Chemistry": "coordination chemistry",
    "Main Group Chemistry": "main group chemistry",
    "Solid State Inorganic Chemistry": "solid state inorganic chemistry",
    "Inorganic Nanomaterials": "inorganic nanomaterials synthesis",
    "General Analytical Chemistry": "analytical chemistry methods",
    "Chromatography": "chromatography techniques",
    "Spectroscopy": "spectroscopy analysis",
    "Electroanalytical Methods": "electroanalytical chemistry",
    "Sensory Analytical Chemistry": "sensory analysis chemistry",
    "Food Analysis": "food analysis chemistry",
    "Environmental Analysis": "environmental analytical chemistry",
    "Chemical Thermodynamics": "chemical thermodynamics",
    "Electrochemistry": "electrochemistry",
    "Quantum Chemistry": "quantum chemistry",
    "Chemical Kinetics": "chemical kinetics",
    "Photochemistry": "photochemistry",
    "Surface Chemistry": "surface chemistry",
    "Solution Chemistry": "solution chemistry",
    "Fluid Mechanics": "fluid mechanics chemistry",
    "General Biochemistry": "biochemistry",
    "Enzymology": "enzymes enzymology",
    "Metabolism": "metabolism biochemistry",
    "Molecular Biology": "molecular biology",
    "Clinical Biochemistry": "clinical biochemistry",
    "Molecular Genetics": "molecular genetics",
    "Proteomics": "proteomics",
    "General Industrial Chemistry": "industrial chemistry",
    "Petrochemicals": "petrochemistry petrochemicals",
    "Chemical Engineering": "chemical engineering",
    "Separation Technologies": "separation technology chemistry",
    "Green Chemistry": "green chemistry sustainable",
    "Industrial Catalysis": "industrial catalysis",
    "Water Treatment": "water treatment chemistry",
    "General Clinical Chemistry": "clinical chemistry",
    "Hematology Analysis": "hematology clinical analysis",
    "Urinalysis": "urinalysis clinical",
    "Hormones": "hormones clinical chemistry",
    "Clinical Toxicology": "clinical toxicology",
    "Biomarkers": "biomarkers clinical",
}
