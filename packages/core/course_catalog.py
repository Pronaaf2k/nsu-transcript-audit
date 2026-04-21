"""
GradeTrace Core — Course Catalog

Centralized repository of all NSU course data, program requirements,
and prerequisite chains. Wraps the data from engine/course_db.py,
engine/audit_engine.py requirement blocks, and engine/prerequisites.py.
"""


class CourseCatalog:
    """NSU course database, program requirements, and prerequisites."""

    # ═══════════════════════════════════════════════════
    # CSE PROGRAM REQUIREMENTS (130 credits)
    # ═══════════════════════════════════════════════════

    CSE_MAJOR_CORE = {
        "CSE173": 3,
        "CSE215": 3, "CSE215L": 1,
        "CSE225": 3, "CSE225L": 1,
        "CSE231": 3, "CSE231L": 1,
        "CSE299": 1,
        "CSE311": 3, "CSE311L": 1,
        "CSE323": 3,
        "CSE325": 3,
        "CSE327": 3,
        "CSE331": 3, "CSE331L": 1,
        "CSE332": 3,
        "CSE373": 3,
        "CSE425": 3,
        "EEE141": 3, "EEE141L": 1,
        "EEE111": 3, "EEE111L": 1,
    }

    CSE_CAPSTONE = {
        "CSE499A": 2,
        "CSE499B": 2,
        "EEE452": 3,
    }

    CSE_SEPS_CORE = {
        "CSE115": 3, "CSE115L": 1,
        "MAT116": 3,
        "MAT120": 3,
        "MAT130": 3,
        "MAT250": 3,
        "MAT125": 3,
        "MAT350": 3,
        "MAT361": 3,
        "PHY107": 3, "PHY107L": 1,
        "PHY108": 3, "PHY108L": 1,
        "CHE101": 3, "CHE101L": 1,
        "BIO103": 3, "BIO103L": 1,
        "CEE110": 1,
    }

    CSE_GED_REQUIRED = {
        "ENG103": 3,
        "ENG105": 3,
        "ENG111": 3,
        "PHI101": 3,
        "PHI104": 3,
        "HIS101": 3,
        "HIS102": 3,
    }

    CSE_GED_CHOICE_1 = {"ECO101": 3, "ECO104": 3}
    CSE_GED_CHOICE_2 = {"POL101": 3, "POL104": 3}
    CSE_GED_CHOICE_3 = {"SOC101": 3, "ANT101": 3, "ENV203": 3, "GEO205": 3}

    CSE_GED_WAIVABLE = {
        "ENG102": 3,
        "MAT112": 0,
    }

    CSE_TOTAL_CREDITS = 130
    CSE_MIN_CGPA = 2.0
    CSE_MAJOR_CORE_CGPA = 2.0
    CSE_MAJOR_ELECTIVE_CGPA = 2.0
    CSE_ELECTIVE_CREDITS = 9
    CSE_OPEN_ELECTIVE_CREDITS = 3

    CSE_ALL_CORE = {**CSE_MAJOR_CORE, **CSE_CAPSTONE, **CSE_SEPS_CORE}

    # ═══════════════════════════════════════════════════
    # BBA PROGRAM REQUIREMENTS — Curriculum 143+
    # ═══════════════════════════════════════════════════

    BBA_SCHOOL_CORE = {
        "ECO101": 3, "ECO104": 3,
        "MIS107": 3, "BUS251": 3,
        "BUS172": 3, "BUS173": 3,
        "BUS135": 3,
    }

    BBA_CORE = {
        "ACT201": 3, "ACT202": 3,
        "FIN254": 3, "LAW200": 3,
        "INB372": 3, "MKT202": 3,
        "MIS207": 3, "MGT212": 3,
        "MGT351": 3, "MGT314": 3,
        "MGT368": 3, "MGT489": 3,
    }

    BBA_GED_WAIVABLE = {"ENG102": 3, "BUS112": 3}

    BBA_GED = {"ENG103": 3, "ENG105": 3, "PHI401": 3}

    BBA_GED_CHOICE_LANG = {"BEN205": 3, "ENG115": 3, "CHN101": 3}
    BBA_GED_CHOICE_HIS = {"HIS101": 3, "HIS102": 3, "HIS103": 3, "HIS205": 3}
    BBA_GED_CHOICE_POL = {"POL101": 3, "POL104": 3, "PAD201": 3}
    BBA_GED_CHOICE_SOC = {"SOC101": 3, "GEO205": 3, "ANT101": 3}
    BBA_GED_CHOICE_SCI = {
        "BIO103": 3, "ENV107": 3, "PBH101": 3,
        "PSY101": 3, "PHY107": 3, "CHE101": 3,
    }
    BBA_GED_CHOICE_LAB = {
        "BIO103L": 1, "ENV107L": 1, "PBH101L": 1,
        "PSY101L": 1, "PHY107L": 1, "CHE101L": 1,
    }

    BBA_INTERNSHIP = {"BUS498": 4}

    BBA_TOTAL_CREDITS = 130
    BBA_MIN_CGPA = 2.0
    BBA_CORE_CGPA = 2.0
    BBA_CONCENTRATION_CGPA = 2.5
    BBA_CONCENTRATION_CREDITS = 18
    BBA_FREE_ELECTIVE_CREDITS = 9

    BBA_ALL_CORE = {**BBA_SCHOOL_CORE, **BBA_CORE}

    # Legacy BBA curriculum (pre-Spring 2014)
    BBA_OLD_TOTAL_CREDITS = 120
    BBA_OLD_MIN_CGPA = 2.0
    BBA_OLD_CORE_CGPA = 2.0

    BBA_OLD_GED_REQUIRED = {
        "ENG102": 3,
        "ENG103": 3,
        "HIS103": 3,
        "PHI101": 3,
        "BEN205": 3,
        "ENV203": 3,
        "PSY101": 3,
    }

    BBA_OLD_CORE_BUSINESS = {
        "ACT201": 3,
        "ACT202": 3,
        "BUS172": 3,
        "ECO101": 3,
        "ECO104": 3,
        "FIN254": 3,
        "MGT210": 3,
        "MGT314": 3,
        "MGT368": 3,
        "MKT202": 3,
        "MIS205": 3,
        "LAW200": 3,
    }

    BBA_OLD_MAJOR_CORE = {
        "BUS101": 3,
        "BUS112": 3,
        "BUS134": 3,
        "BUS251": 3,
        "BUS401": 3,
        "BUS498": 4,
        "MGT321": 3,
        "MGT489": 3,
        "QM212": 3,
    }

    BBA_OLD_ALL_CORE = {**BBA_OLD_CORE_BUSINESS, **BBA_OLD_MAJOR_CORE}

    # ═══════════════════════════════════════════════════
    # BBA CONCENTRATIONS (18cr each: 4 required + 2 elective)
    # ═══════════════════════════════════════════════════

    BBA_CONC_ACT_REQUIRED = {"ACT310": 3, "ACT320": 3, "ACT360": 3, "ACT370": 3}
    BBA_CONC_ACT_ELECTIVE = {"ACT380": 3, "ACT460": 3, "ACT430": 3, "ACT410": 3}

    BBA_CONC_FIN_REQUIRED = {"FIN433": 3, "FIN440": 3, "FIN435": 3, "FIN444": 3}
    BBA_CONC_FIN_ELECTIVE = {"FIN455": 3, "FIN464": 3, "FIN470": 3, "FIN480": 3, "FIN410": 3}

    BBA_CONC_MKT_REQUIRED = {"MKT337": 3, "MKT344": 3, "MKT460": 3, "MKT470": 3}
    BBA_CONC_MKT_ELECTIVE = {
        "MKT412": 3, "MKT465": 3, "MKT382": 3, "MKT417": 3,
        "MKT330": 3, "MKT450": 3, "MKT355": 3, "MKT445": 3, "MKT475": 3,
    }

    BBA_CONC_MGT_REQUIRED = {"MGT321": 3, "MGT330": 3, "HRM370": 3, "MGT410": 3}
    BBA_CONC_MGT_ELECTIVE = {"MGT350": 3, "MGT490": 3, "HRM470": 3, "HRM450": 3, "MIS320": 3}

    BBA_CONC_HRM_REQUIRED = {"HRM340": 3, "HRM360": 3, "HRM380": 3, "HRM450": 3}
    BBA_CONC_HRM_ELECTIVE = {"HRM370": 3, "HRM499": 3, "HRM470": 3}

    BBA_CONC_MIS_REQUIRED = {"MIS210": 3, "MIS310": 3, "MIS320": 3, "MIS470": 3}
    BBA_CONC_MIS_ELECTIVE = {"MIS330": 3, "MIS410": 3, "MIS450": 3, "MGT490": 3, "MIS499": 3}

    BBA_CONC_SCM_REQUIRED = {"SCM310": 3, "SCM320": 3, "SCM450": 3, "MGT460": 3}
    BBA_CONC_SCM_ELECTIVE = {"MGT360": 3, "MGT390": 3, "MGT470": 3, "MGT490": 3}

    BBA_CONC_ECO_REQUIRED = {"ECO201": 3, "ECO204": 3, "ECO348": 3, "ECO328": 3}
    BBA_CONC_ECO_ELECTIVE = {
        "ECO244": 3, "ECO301": 3, "ECO304": 3, "ECO317": 3, "ECO329": 3,
        "ECO343": 3, "ECO354": 3, "ECO360": 3, "ECO372": 3, "ECO380": 3,
        "ECO406": 3, "ECO410": 3, "ECO414": 3, "ECO415": 3, "ECO417": 3,
        "ECO430": 3, "ECO436": 3, "ECO441": 3, "ECO443": 3, "ECO450": 3,
        "ECO451": 3, "ECO460": 3, "ECO465": 3, "ECO472": 3, "ECO474": 3,
        "ECO475": 3, "ECO484": 3, "ECO485": 3, "ECO486": 3, "ECO492": 3,
    }

    BBA_CONC_INB_REQUIRED = {"INB400": 3, "INB490": 3, "INB480": 3, "MKT382": 3}
    BBA_CONC_INB_ELECTIVE = {
        "INB410": 3, "INB350": 3, "INB355": 3, "INB415": 3,
        "INB450": 3, "INB495": 3, "MKT417": 3,
    }

    BBA_CONCENTRATIONS = {
        "ACT": (BBA_CONC_ACT_REQUIRED, BBA_CONC_ACT_ELECTIVE, "Accounting"),
        "FIN": (BBA_CONC_FIN_REQUIRED, BBA_CONC_FIN_ELECTIVE, "Finance"),
        "MKT": (BBA_CONC_MKT_REQUIRED, BBA_CONC_MKT_ELECTIVE, "Marketing"),
        "MGT": (BBA_CONC_MGT_REQUIRED, BBA_CONC_MGT_ELECTIVE, "Management"),
        "HRM": (BBA_CONC_HRM_REQUIRED, BBA_CONC_HRM_ELECTIVE, "Human Resource Management"),
        "MIS": (BBA_CONC_MIS_REQUIRED, BBA_CONC_MIS_ELECTIVE, "Management Information Systems"),
        "SCM": (BBA_CONC_SCM_REQUIRED, BBA_CONC_SCM_ELECTIVE, "Supply Chain Management"),
        "ECO": (BBA_CONC_ECO_REQUIRED, BBA_CONC_ECO_ELECTIVE, "Economics"),
        "INB": (BBA_CONC_INB_REQUIRED, BBA_CONC_INB_ELECTIVE, "International Business"),
    }

    VALID_CONCENTRATIONS = set(BBA_CONCENTRATIONS.keys())

    # ═══════════════════════════════════════════════════
    # PREREQUISITES
    # ═══════════════════════════════════════════════════

    PREREQUISITES_CSE = {
        # ── Programming & Software Track ──
        # Direct Entry → CSE115 (no prereq)
        "CSE215":  ["CSE115"],          # CSE115/L → CSE215+L
        "CSE215L": ["CSE115L"],
        "CSE225":  ["CSE215"],          # CSE215/L → CSE225+L
        "CSE225L": ["CSE215L"],
        "CSE373":  ["CSE225"],          # CSE225/L → CSE373
        "CSE311":  ["CSE225", "CSE173"],  # CSE225/L + CSE173 → CSE311+L
        "CSE311L": ["CSE225L"],
        "CSE498":  ["CSE327"],          # CSE327 → CSE498 (+ ~100 credits)

        # ── Mathematics & Physical Science Track ──
        # Direct Entry → MAT120 (no prereq, MAT116 is remedial)
        "MAT130":  ["MAT120"],          # MAT120 → MAT130
        "MAT250":  ["MAT130"],          # MAT130 → MAT250
        "MAT350":  ["MAT250"],          # MAT250 → MAT350
        "EEE141":  ["MAT120", "PHY107"],  # MAT120 + PHY107 → EEE141+L
        "EEE141L": ["MAT120", "PHY107"],
    }

    PREREQUISITES_BBA = {
        # ── Quantitative & Finance Track ──
        # Direct Entry → BUS135 (no prereq)
        "BUS172":  ["BUS135"],          # BUS135 → BUS172
        "BUS173":  ["BUS172"],          # BUS172 → BUS173
        "FIN254":  ["BUS135", "ACT201"],  # BUS135 + ACT201 → FIN254
        "FIN440":  ["FIN254"],          # FIN254 → FIN440

        # ── Accounting Track ──
        # Direct Entry → ACT201 (no prereq)
        "ACT202":  ["ACT201"],          # ACT201 → ACT202
        "ACT310":  ["ACT201"],          # ACT201 → ACT310

        # ── English Track ──
        "ENG103":  ["ENG102"],
        "ENG105":  ["ENG103"],

        # ── Economics Track ──
        "ECO104":  ["ECO101"],

        # ── Management Track ──
        "MGT351":  ["MGT212"],
        "MGT314":  ["MGT212"],
        "MGT368":  ["MGT212"],
        "MGT489":  ["FIN254", "MKT202", "MGT212"],
    }

    # ═══════════════════════════════════════════════════
    # ALL_COURSES — Unified lookup (code → (name, credits))
    # Built from engine/course_db.py
    # ═══════════════════════════════════════════════════

    # CSE courses
    _CSE_MAJOR_CORE_DB = {
        "CSE173": ("Discrete Mathematics", 3),
        "CSE215": ("Programming Language II", 3),
        "CSE215L": ("Programming Language II Lab", 1),
        "CSE225": ("Data Structures & Algorithms", 3),
        "CSE225L": ("Data Structures & Algorithms Lab", 1),
        "CSE231": ("Digital Logic Design", 3),
        "CSE231L": ("Digital Logic Design Lab", 1),
        "CSE299": ("Junior Design Project", 1),
        "CSE311": ("Database Management Systems", 3),
        "CSE311L": ("Database Management Systems Lab", 1),
        "CSE323": ("Operating Systems Design", 3),
        "CSE325": ("Operating Systems", 3),
        "CSE327": ("Software Engineering", 3),
        "CSE331": ("Microprocessor Interfacing & Embedded", 3),
        "CSE331L": ("Microprocessor Interfacing Lab", 1),
        "CSE332": ("Computer Organization & Architecture", 3),
        "CSE373": ("Design & Analysis of Algorithms", 3),
        "CSE425": ("Concepts of Programming Languages", 3),
        "EEE141": ("Electrical Circuits I", 3),
        "EEE141L": ("Electrical Circuits I Lab", 1),
        "EEE111": ("Analog Electronics I", 3),
        "EEE111L": ("Analog Electronics I Lab", 1),
    }

    _CSE_CAPSTONE_DB = {
        "CSE499A": ("Senior Capstone Design I", 2),
        "CSE499B": ("Senior Capstone Design II", 2),
        "EEE452": ("Engineering Economics", 3),
    }

    _CSE_SEPS_DB = {
        "CSE115": ("Programming Language I", 3),
        "CSE115L": ("Programming Language I Lab", 1),
        "MAT116": ("Pre-Calculus", 3),
        "MAT120": ("Calculus I", 3),
        "MAT125": ("Linear Algebra", 3),
        "MAT130": ("Calculus II", 3),
        "MAT250": ("Calculus III", 3),
        "MAT350": ("Complex Variables", 3),
        "MAT361": ("Discrete Mathematics II", 3),
        "PHY107": ("Physics I", 3),
        "PHY107L": ("Physics I Lab", 1),
        "PHY108": ("Physics II", 3),
        "PHY108L": ("Physics II Lab", 1),
        "CHE101": ("Chemistry I", 3),
        "CHE101L": ("Chemistry I Lab", 1),
        "BIO103": ("Biology I", 3),
        "BIO103L": ("Biology I Lab", 1),
        "CEE110": ("Engineering Drawing", 1),
    }

    _CSE_GED_DB = {
        "ENG103": ("Intermediate Composition", 3),
        "ENG105": ("Advanced Writing Skills", 3),
        "ENG111": ("Public Speaking", 3),
        "PHI101": ("Introduction to Philosophy", 3),
        "PHI104": ("Introduction to Ethics", 3),
        "HIS101": ("Bangladesh History & Culture", 3),
        "HIS102": ("World Civilization", 3),
        "CSE101": ("Intro to Python Programming", 3),
        "CSE145": ("Intro to AI", 3),
        "CSE226": ("Fundamentals of Vibe Coding", 3),
        "ECO101": ("Intro to Microeconomics", 3),
        "ECO104": ("Intro to Macroeconomics", 3),
        "POL101": ("Intro to Political Science", 3),
        "POL104": ("Political Science", 3),
        "SOC101": ("Intro to Sociology", 3),
        "ANT101": ("Anthropology", 3),
        "ENV203": ("Environmental Studies", 3),
        "GEO205": ("Geography", 3),
    }

    _CSE_ELECTIVES_400_DB = {
        "CSE421": ("Machine Learning", 3),
        "CSE422": ("Simulation and Modeling", 3),
        "CSE423": ("Advanced Operating Systems", 3),
        "CSE424": ("Object-Oriented Software Dev", 3),
        "CSE427": ("Software Quality Assurance", 3),
        "CSE428": ("Software Project Management", 3),
        "CSE429": ("Software System Architecture", 3),
        "CSE433": ("Advanced Computer Architecture", 3),
        "CSE438": ("Networks & Distributed Systems", 3),
        "CSE439": ("Advanced Computer Networks", 3),
        "CSE440": ("Artificial Intelligence (Adv)", 3),
        "CSE445": ("Machine Learning (Adv)", 3),
        "CSE448": ("Neural Networks", 3),
        "CSE465": ("Pattern Recognition", 3),
        "CSE467": ("Image Processing", 3),

        "CSE472": ("Advanced Algorithms", 3),
        "CSE473": ("Parallel Processing", 3),
        "CSE474": ("Computational Complexity", 3),
        "CSE475": ("Automata Theory & Formal Language", 3),
        "CSE478": ("Graph Theory", 3),
    }

    # BBA courses
    _BBA_SCHOOL_CORE_DB = {
        "ECO101": ("Intro to Microeconomics", 3),
        "ECO104": ("Intro to Macroeconomics", 3),
        "MIS107": ("Introduction to Computers", 3),
        "BUS251": ("Business Communication", 3),
        "BUS172": ("Introduction to Statistics", 3),
        "BUS173": ("Applied Statistics", 3),
        "BUS135": ("Business Mathematics", 3),
    }

    _BBA_CORE_DB = {
        "ACT201": ("Intro to Financial Accounting", 3),
        "ACT202": ("Intro to Managerial Accounting", 3),
        "FIN254": ("Intro to Financial Management", 3),
        "LAW200": ("Legal Environment of Business", 3),
        "INB372": ("International Business", 3),
        "MKT202": ("Introduction to Marketing", 3),
        "MIS207": ("Management Information Systems", 3),
        "MGT212": ("Principles of Management", 3),
        "MGT351": ("Human Resource Management", 3),
        "MGT314": ("Production Management", 3),
        "MGT368": ("Entrepreneurship", 3),
        "MGT489": ("Strategic Management", 3),
    }

    _BBA_GED_DB = {
        "ENG103": ("Intermediate Composition", 3),
        "ENG105": ("Advanced Composition", 3),
        "PHI401": ("Ethics / Philosophy", 3),
        "BEN205": ("Bengali Literature", 3),
        "ENG115": ("Advanced English", 3),
        "CHN101": ("Chinese Language", 3),
        "HIS101": ("Bangladesh History & Culture", 3),
        "HIS102": ("World Civilization", 3),
        "HIS103": ("History of South Asia", 3),
        "HIS205": ("History of Science", 3),
        "POL101": ("Intro to Political Science", 3),
        "POL104": ("Political Science", 3),
        "PAD201": ("Public Administration", 3),
        "SOC101": ("Intro to Sociology", 3),
        "GEO205": ("Geography", 3),
        "ANT101": ("Anthropology", 3),
        "BIO103": ("Biology I", 3),
        "ENV107": ("Environmental Science", 3),
        "PBH101": ("Public Health", 3),
        "PSY101": ("Intro to Psychology", 3),
        "PHY107": ("Physics I", 3),
        "CHE101": ("Chemistry I", 3),
        "BIO103L": ("Biology I Lab", 1),
        "ENV107L": ("Environmental Science Lab", 1),
        "PBH101L": ("Public Health Lab", 1),
        "PSY101L": ("Intro to Psychology Lab", 1),
        "PHY107L": ("Physics I Lab", 1),
        "CHE101L": ("Chemistry I Lab", 1),
        "BUS498": ("Internship", 4),
    }

    _WAIVER_COURSES_DB = {
        "ENG102": ("Introduction to Composition", 3),
        "MAT112": ("College Algebra", 0),
        "BUS112": ("Intro to Business Mathematics", 3),
    }

    # BBA concentration course DB (code → (name, credits))
    _BBA_CONC_DB = {
        # ACT
        "ACT310": ("Intermediate Accounting I", 3), "ACT320": ("Intermediate Accounting II", 3),
        "ACT360": ("Advanced Managerial Accounting", 3), "ACT370": ("Taxation", 3),
        "ACT380": ("Accounting Info Systems", 3), "ACT460": ("International Accounting", 3),
        "ACT430": ("Forensic Accounting", 3), "ACT410": ("Advanced Accounting", 3),
        # FIN
        "FIN433": ("Investment Analysis", 3), "FIN440": ("International Finance", 3),
        "FIN435": ("Financial Institutions", 3), "FIN444": ("Financial Markets", 3),
        "FIN455": ("Derivatives", 3), "FIN464": ("Corporate Finance", 3),
        "FIN470": ("Insurance and Risk Management", 3), "FIN480": ("Behavioural Finance", 3),
        "FIN410": ("Financial Statement Analysis", 3),
        # MKT
        "MKT337": ("Promotional Management", 3), "MKT344": ("Consumer Behaviour", 3),
        "MKT460": ("Strategic Marketing", 3), "MKT470": ("Marketing Research", 3),
        "MKT412": ("Services Marketing", 3), "MKT465": ("Brand Management", 3),
        "MKT382": ("International Marketing", 3), "MKT417": ("Export-Import Management", 3),
        "MKT330": ("Digital Marketing", 3), "MKT450": ("Marketing Channels", 3),
        "MKT355": ("Retail Management", 3), "MKT445": ("Sales Management", 3),
        "MKT475": ("Marketing Analytics", 3),
        # MGT
        "MGT321": ("Organizational Behavior", 3), "MGT330": ("Designing Effective Orgs", 3),
        "MGT410": ("Org Development & Change", 3),
        "MGT350": ("Managing Quality", 3), "MGT490": ("Project Management", 3),
        "MIS320": ("IT for Managers", 3),
        # HRM
        "HRM340": ("Training and Development", 3), "HRM360": ("Planning and Staffing", 3),
        "HRM380": ("Compensation Theory and Practice", 3), "HRM450": ("Industrial Relations", 3),
        "HRM370": ("Managerial Skill Development", 3), "HRM499": ("HRM Capstone", 3),
        "HRM470": ("Negotiations", 3),
        # MIS
        "MIS210": ("Concepts of Computer Programming", 3), "MIS310": ("Systems Analysis & Design", 3),
        "MIS470": ("Management of IT", 3),
        "MIS330": ("Digital Marketing & Social Networks", 3), "MIS410": ("Business Intelligence", 3),
        "MIS450": ("ERP Systems", 3), "MIS499": ("MIS Capstone", 3),
        # SCM
        "SCM310": ("Supply Chain Fundamentals", 3), "SCM320": ("Supply Chain Planning", 3),
        "SCM450": ("Advanced Supply Chain", 3), "MGT460": ("Operations Management", 3),
        "MGT360": ("Global Supply Chain", 3), "MGT390": ("Warehouse Management", 3),
        "MGT470": ("Quality Management", 3),
        # ECO
        "ECO201": ("Intermediate Microeconomics", 3), "ECO204": ("Intermediate Macroeconomics", 3),
        "ECO348": ("Mathematical Economics", 3), "ECO328": ("Econometrics", 3),
        "ECO244": ("Applied Economics", 3), "ECO301": ("Microeconomic Theory", 3),
        "ECO304": ("Macroeconomic Theory", 3), "ECO317": ("Money & Banking", 3),
        "ECO329": ("Applied Econometrics", 3), "ECO343": ("Public Finance", 3),
        "ECO354": ("Development Economics", 3), "ECO360": ("International Trade", 3),
        "ECO372": ("Bangladesh Economy", 3), "ECO380": ("Health Economics", 3),
        "ECO406": ("Economic Policy", 3), "ECO410": ("Game Theory", 3),
        "ECO414": ("Urban Economics", 3), "ECO415": ("Time Series", 3),
        "ECO417": ("Financial Economics", 3), "ECO430": ("Managerial Economics", 3),
        "ECO436": ("Environmental Economics", 3), "ECO441": ("Labor Economics", 3),
        "ECO443": ("Industrial Organization", 3), "ECO450": ("Research Methods", 3),
        "ECO451": ("Monetary Economics", 3), "ECO460": ("International Finance", 3),
        "ECO465": ("Political Economy", 3), "ECO472": ("Economic History", 3),
        "ECO474": ("Economic Growth", 3), "ECO475": ("Panel Data", 3),
        "ECO484": ("Experimental Economics", 3), "ECO485": ("Behavioural Economics", 3),
        "ECO486": ("Neuroeconomics", 3), "ECO492": ("Special Topics", 3),
        # INB
        "INB400": ("International Business Strategy", 3), "INB490": ("INB Capstone", 3),
        "INB480": ("Global Operations", 3),
        "INB410": ("Cross-Cultural Management", 3), "INB350": ("Global Marketing", 3),
        "INB355": ("Global Finance", 3), "INB415": ("International Negotiations", 3),
        "INB450": ("Global Entrepreneurship", 3), "INB495": ("Special Topics in INB", 3),
    }

    @classmethod
    def build_all_courses(cls) -> dict:
        """Build the unified ALL_COURSES lookup: code → (name, credits)."""
        all_courses = {}
        dbs = [
            cls._CSE_MAJOR_CORE_DB, cls._CSE_CAPSTONE_DB, cls._CSE_SEPS_DB,
            cls._CSE_GED_DB, cls._CSE_ELECTIVES_400_DB,
            cls._BBA_SCHOOL_CORE_DB, cls._BBA_CORE_DB, cls._BBA_GED_DB,
            cls._WAIVER_COURSES_DB, cls._BBA_CONC_DB,
        ]
        for db in dbs:
            all_courses.update(db)
        return all_courses

    @classmethod
    def get_prerequisites(cls, program: str) -> dict:
        """Return the prerequisite map for the given program."""
        if program.upper() == "CSE":
            return cls.PREREQUISITES_CSE
        return cls.PREREQUISITES_BBA

    @classmethod
    def is_valid_course(cls, code: str) -> bool:
        """Check if a course code exists in the NSU database."""
        return code in cls.build_all_courses()

    @classmethod
    def get_concentration_info(cls, conc_code: str) -> tuple | None:
        """Return (required_dict, elective_dict, label) for a BBA concentration."""
        return cls.BBA_CONCENTRATIONS.get(conc_code.upper())


# Pre-built lookup for use by CourseRecord and other modules
ALL_COURSES = CourseCatalog.build_all_courses()
