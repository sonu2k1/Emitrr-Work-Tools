"""
EHR & Patient Portal Signatures Database
Contains accurate signatures, domain patterns, URL regexes, and word-boundary heuristics
for 50+ healthcare EHR / portal providers.
"""

import re
from urllib.parse import urlparse

# Major EHR / Patient Portal Provider Signatures
EHR_SIGNATURES = [
    {
        "name": "Epic (MyChart / Patient Gateway / My CS-Link)",
        "category": "Hospital & Health System EHR",
        "domain_patterns": [
            r"mychart[a-zA-Z0-9\.\-_]*\.(org|com|net|edu)",
            r"myhealth[a-zA-Z0-9\.\-_]*\.(org|com|net|edu)/mychart",
            r"mycslink\.org",
            r"patientgateway\.org",
            r"patientgateway\.massgeneralbrigham\.org",
            r"epichosted\.com",
            r"mychartrx\.",
            r"mycareanywhere\."
        ],
        "url_regexes": [
            r"/mychart(/|$|\?)",
            r"mychart\.",
            r"mycslink",
            r"patientgateway"
        ],
        "page_keywords": [
            r"\bmychart\b",
            r"\bepic mychart\b",
            r"\bepic systems\b",
            r"\bmy cs-link\b",
            r"\bpatient gateway\b",
            r"\bmychart portal\b",
            r"\bpowered by mychart\b"
        ]
    },
    {
        "name": "AthenaHealth (AthenaPatient / Communicator)",
        "category": "Cloud EHR & Practice Management",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*portal\.athenahealth\.com",
            r"[a-zA-Z0-9\.\-_]*platform\.athenahealth\.com",
            r"athenahealth\.com/patient",
            r"athenanet\.athenahealth\.com",
            r"patientpayment\.athenahealth\.com",
            r"athenacommunicator\.com",
            r"athenapatient\.com"
        ],
        "url_regexes": [
            r"portal\.athenahealth\.com",
            r"platform\.athenahealth\.com",
            r"athenanet\.athenahealth\.com",
            r"athenacommunicator\.com",
            r"athenapatient\.com"
        ],
        "page_keywords": [
            r"\bathenahealth\b",
            r"\bathenanet\b",
            r"\bathenapatient\b",
            r"\bathena patient portal\b",
            r"\bathena communicator\b"
        ]
    },
    {
        "name": "eClinicalWorks (Healow / mycw)",
        "category": "Ambulatory EHR & Practice Portal",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*healow\.com",
            r"[a-zA-Z0-9\.\-_]*mycw\.net",
            r"[a-zA-Z0-9\.\-_]*ecwcloud\.com",
            r"eclinicalweb\.com",
            r"eclinicalworks\.com",
            r"healowpay\.com",
            r"patientportal\.eclinicalworks\.com"
        ],
        "url_regexes": [
            r"healow\.com",
            r"mycw\.net",
            r"ecwcloud\.com",
            r"healowpay\.com",
            r"eclinicalweb\.com",
            r"/healow(/|$|\?)"
        ],
        "page_keywords": [
            r"\bhealow\b",
            r"\beclinicalworks\b",
            r"\bmycw\.net\b",
            r"\bhealow patient portal\b",
            r"\bpowered by healow\b"
        ]
    },
    {
        "name": "ModMed (EMA / Modernizing Medicine / gMed)",
        "category": "Specialty EHR (Derm, Gastro, Ortho, Ophthalmology, ENT)",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*\.ema\.md",
            r"[a-zA-Z0-9\.\-_]*modmed\.com",
            r"[a-zA-Z0-9\.\-_]*mygportal\.com",
            r"myehr\.com",
            r"modernizingmedicine\.com",
            r"gmed\.com",
            r"modmedportal\.com"
        ],
        "url_regexes": [
            r"\.ema\.md(/|$|\?)",
            r"modmed\.com",
            r"mygportal\.com",
            r"myehr\.com",
            r"modernizingmedicine\.com"
        ],
        "page_keywords": [
            r"\bmodernizing medicine\b",
            r"\bmodmed\b",
            r"\bema portal\b",
            r"\bema patient portal\b",
            r"\bgmed\b",
            r"\bggastro\b",
            r"\bmodmed patient portal\b"
        ]
    },
    {
        "name": "NextGen Healthcare (NextMD)",
        "category": "Ambulatory EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*nextmd\.com",
            r"[a-zA-Z0-9\.\-_]*nextgen\.com",
            r"myhealthchart\.nextmd\.com"
        ],
        "url_regexes": [
            r"nextmd\.com",
            r"nextgen\.com"
        ],
        "page_keywords": [
            r"\bnextmd\b",
            r"\bnextgen healthcare\b",
            r"\bnextgen patient portal\b",
            r"\bnextgen\b"
        ]
    },
    {
        "name": "Cerner / Oracle Health (HealtheLife)",
        "category": "Hospital & Health System EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*healthelife\.com",
            r"[a-zA-Z0-9\.\-_]*cernerhealth\.com",
            r"[a-zA-Z0-9\.\-_]*mycerner\.com"
        ],
        "url_regexes": [
            r"healthelife\.com",
            r"cernerhealth\.com",
            r"mycerner\.com"
        ],
        "page_keywords": [
            r"\bhealthelife\b",
            r"\bcerner health\b",
            r"\boracle health\b",
            r"\bcerner\b"
        ]
    },
    {
        "name": "Allscripts / Veradigm (FollowMyHealth)",
        "category": "EHR & Patient Engagement",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*followmyhealth\.com",
            r"veradigm\.com",
            r"allscripts\.com"
        ],
        "url_regexes": [
            r"followmyhealth\.com",
            r"veradigm\.com"
        ],
        "page_keywords": [
            r"\bfollowmyhealth\b",
            r"\bfollow my health\b",
            r"\bveradigm\b",
            r"\ballscripts\b"
        ]
    },
    {
        "name": "Greenway Health (MyHealthRecord / PrimeSuite / Intergy)",
        "category": "Ambulatory EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*myhealthrecord\.com",
            r"greenwayhealth\.com",
            r"primesuite\.com",
            r"intergy\.com"
        ],
        "url_regexes": [
            r"myhealthrecord\.com",
            r"greenwayhealth\.com"
        ],
        "page_keywords": [
            r"\bmyhealthrecord\b",
            r"\bgreenway health\b",
            r"\bprimesuite\b",
            r"\bintergy\b"
        ]
    },
    {
        "name": "Kareo / Tebra",
        "category": "Independent Practice Cloud EHR",
        "domain_patterns": [
            r"portal\.kareo\.com",
            r"patientportal\.kareo\.com",
            r"tebra\.com",
            r"kareo\.com"
        ],
        "url_regexes": [
            r"portal\.kareo\.com",
            r"tebra\.com/patient"
        ],
        "page_keywords": [
            r"\bkareo\b",
            r"\btebra\b",
            r"\bkareo patient portal\b",
            r"\btebra portal\b"
        ]
    },
    {
        "name": "AdvancedMD",
        "category": "Cloud Practice Management & EHR",
        "domain_patterns": [
            r"patientportal\.advancedmd\.com",
            r"[a-zA-Z0-9\.\-_]*advancedmd\.com"
        ],
        "url_regexes": [
            r"patientportal\.advancedmd\.com",
            r"advancedmd\.com/portal"
        ],
        "page_keywords": [
            r"\badvancedmd\b",
            r"\badvancedmd portal\b"
        ]
    },
    {
        "name": "DrChrono (OnPatient)",
        "category": "Cloud EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*onpatient\.com",
            r"drchrono\.com"
        ],
        "url_regexes": [
            r"onpatient\.com",
            r"drchrono\.com/patient"
        ],
        "page_keywords": [
            r"\bonpatient\b",
            r"\bdrchrono\b",
            r"\bonpatient portal\b"
        ]
    },
    {
        "name": "WebPT",
        "category": "Physical & Occupational Therapy EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*webpt\.com",
            r"therabill\.com"
        ],
        "url_regexes": [
            r"webpt\.com",
            r"therabill\.com"
        ],
        "page_keywords": [
            r"\bwebpt\b",
            r"\btherabill\b"
        ]
    },
    {
        "name": "Practice Fusion (Patient Fusion)",
        "category": "Cloud EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*patientfusion\.com",
            r"practicefusion\.com"
        ],
        "url_regexes": [
            r"patientfusion\.com"
        ],
        "page_keywords": [
            r"\bpatient fusion\b",
            r"\bpatientfusion\b",
            r"\bpractice fusion\b"
        ]
    },
    {
        "name": "ChiroTouch (CT InTouch / ChiroNeo)",
        "category": "Chiropractic EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*ctintouch\.com",
            r"[a-zA-Z0-9\.\-_]*chironeo\.com",
            r"mychirotouch\.com"
        ],
        "url_regexes": [
            r"ctintouch\.com",
            r"chironeo\.com",
            r"mychirotouch\.com"
        ],
        "page_keywords": [
            r"\bchirotouch\b",
            r"\bct intouch\b",
            r"\bchironeo\b"
        ]
    },
    {
        "name": "IntakeQ",
        "category": "Online Intake & Client Portal",
        "domain_patterns": [
            r"intakeq\.com",
            r"secure\.intakeq\.com"
        ],
        "url_regexes": [
            r"intakeq\.com"
        ],
        "page_keywords": [
            r"\bintakeq\b",
            r"\bintake q\b"
        ]
    },
    {
        "name": "Jane App",
        "category": "Health & Wellness Practice Management",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*\.jane\.app",
            r"janeapp\.com"
        ],
        "url_regexes": [
            r"\.jane\.app(/|$|\?)"
        ],
        "page_keywords": [
            r"\bjane app\b",
            r"\bjane\.app\b",
            r"\bpowered by jane\b"
        ]
    },
    {
        "name": "SimplePractice",
        "category": "Behavioral Health Practice Management",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*\.clientsecure\.me",
            r"simplepractice\.com"
        ],
        "url_regexes": [
            r"clientsecure\.me",
            r"simplepractice\.com"
        ],
        "page_keywords": [
            r"\bsimplepractice\b",
            r"\bsimple practice\b",
            r"\bclientsecure\.me\b"
        ]
    },
    {
        "name": "TherapyNotes",
        "category": "Behavioral Health EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*therapyportal\.com",
            r"therapynotes\.com"
        ],
        "url_regexes": [
            r"therapyportal\.com"
        ],
        "page_keywords": [
            r"\btherapyportal\b",
            r"\btherapy notes\b",
            r"\btherapynotes\b"
        ]
    },
    {
        "name": "Nextech (MyNextech)",
        "category": "Plastic Surgery, Derm & Ophtha EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*mynextech\.com",
            r"nextech\.com"
        ],
        "url_regexes": [
            r"mynextech\.com"
        ],
        "page_keywords": [
            r"\bmynextech\b",
            r"\bnextech\b"
        ]
    },
    {
        "name": "Phreesia",
        "category": "Patient Intake & Registration",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*phreesia\.net",
            r"phreesia\.com",
            r"phreesia-intake\.com"
        ],
        "url_regexes": [
            r"phreesia\.net",
            r"phreesia-intake\.com"
        ],
        "page_keywords": [
            r"\bphreesia\b",
            r"\bphreesia registration\b"
        ]
    },
    {
        "name": "NexHealth",
        "category": "Dental & Medical Patient Experience",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*nexhealth\.com",
            r"nexhealth\.io"
        ],
        "url_regexes": [
            r"nexhealth\.com",
            r"nexhealth\.io"
        ],
        "page_keywords": [
            r"\bnexhealth\b",
            r"\bpowered by nexhealth\b"
        ]
    },
    {
        "name": "Solutionreach (SR Patient)",
        "category": "Patient Engagement & Portal",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*srpatient\.com",
            r"solutionreach\.com",
            r"smile-reminder\.com"
        ],
        "url_regexes": [
            r"srpatient\.com",
            r"solutionreach\.com"
        ],
        "page_keywords": [
            r"\bsr patient\b",
            r"\bsolutionreach\b"
        ]
    },
    {
        "name": "CareCloud (Breeze)",
        "category": "Cloud EHR",
        "domain_patterns": [
            r"breeze\.carecloud\.com",
            r"[a-zA-Z0-9\.\-_]*carecloud\.com"
        ],
        "url_regexes": [
            r"breeze\.carecloud\.com"
        ],
        "page_keywords": [
            r"\bcarecloud breeze\b",
            r"\bcarecloud\b"
        ]
    },
    {
        "name": "CharmHealth",
        "category": "Cloud EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*charmtracker\.com",
            r"[a-zA-Z0-9\.\-_]*charmphr\.com",
            r"charmhealth\.com"
        ],
        "url_regexes": [
            r"charmtracker\.com",
            r"charmphr\.com"
        ],
        "page_keywords": [
            r"\bcharmhealth\b",
            r"\bcharm phr\b"
        ]
    },
    {
        "name": "PrognoCIS (Bizmatics)",
        "category": "Specialty EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*prognocis\.com",
            r"bizmatics\.com"
        ],
        "url_regexes": [
            r"prognocis\.com"
        ],
        "page_keywords": [
            r"\bprognocis\b"
        ]
    },
    {
        "name": "Aprima / e-MDs",
        "category": "Ambulatory EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*myhealthpatientportal\.com",
            r"aprima\.com",
            r"e-mds\.com"
        ],
        "url_regexes": [
            r"myhealthpatientportal\.com"
        ],
        "page_keywords": [
            r"\baprima\b",
            r"\be-mds\b"
        ]
    },
    {
        "name": "Compulink (Advantage EHR)",
        "category": "Optometry & Specialty EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*mycompulink\.com",
            r"compulinkadvantage\.com"
        ],
        "url_regexes": [
            r"mycompulink\.com"
        ],
        "page_keywords": [
            r"\bcompulink\b",
            r"\bcompulink advantage\b"
        ]
    },
    {
        "name": "Crystal Practice Management (Crystal PM)",
        "category": "Optometry EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*crystalpm\.com",
            r"crystalpm\.net"
        ],
        "url_regexes": [
            r"crystalpm\.com"
        ],
        "page_keywords": [
            r"\bcrystal pm\b",
            r"\bcrystalpm\b"
        ]
    },
    {
        "name": "Eyefinity / Officemate",
        "category": "Eye Care EHR",
        "domain_patterns": [
            r"eoportal\.eyefinity\.com",
            r"[a-zA-Z0-9\.\-_]*eyefinity\.com"
        ],
        "url_regexes": [
            r"eyefinity\.com"
        ],
        "page_keywords": [
            r"\beyefinity\b",
            r"\bofficemate\b"
        ]
    },
    {
        "name": "Dentrix / Patient Engage (Henry Schein)",
        "category": "Dental EHR & Practice Software",
        "domain_patterns": [
            r"patientconnections\.com",
            r"eforms\.dentrix\.com",
            r"dentrixhub\.com"
        ],
        "url_regexes": [
            r"patientconnections\.com",
            r"dentrix"
        ],
        "page_keywords": [
            r"\bdentrix\b",
            r"\bpatient connections\b",
            r"\bhenry schein\b"
        ]
    },
    {
        "name": "Eaglesoft / Patterson Dental",
        "category": "Dental EHR",
        "domain_patterns": [
            r"pattersondental\.com",
            r"eaglesoft\.net"
        ],
        "url_regexes": [
            r"eaglesoft",
            r"pattersondental"
        ],
        "page_keywords": [
            r"\beaglesoft\b",
            r"\bpatterson dental\b"
        ]
    },
    {
        "name": "Curve Dental (Curve Hero)",
        "category": "Cloud Dental Software",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*curvehero\.com",
            r"curvedental\.com"
        ],
        "url_regexes": [
            r"curvehero\.com"
        ],
        "page_keywords": [
            r"\bcurve dental\b",
            r"\bcurve hero\b"
        ]
    },
    {
        "name": "Open Dental",
        "category": "Dental Practice Management",
        "domain_patterns": [
            r"patientportal\.opendental\.com",
            r"opendental\.com"
        ],
        "url_regexes": [
            r"patientportal\.opendental\.com"
        ],
        "page_keywords": [
            r"\bopen dental\b"
        ]
    },
    {
        "name": "Elation Health (Passport)",
        "category": "Primary Care Cloud EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*elationpassport\.com",
            r"elationhealth\.com"
        ],
        "url_regexes": [
            r"elationpassport\.com"
        ],
        "page_keywords": [
            r"\belation health\b",
            r"\belation passport\b"
        ]
    },
    {
        "name": "Nextech (MyPatientVisit / MyNextech)",
        "category": "Specialty EHR (Derm, Ophtha, Plastic)",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*mypatientvisit\.com",
            r"[a-zA-Z0-9\.\-_]*mynextech\.com",
            r"nextech\.com"
        ],
        "url_regexes": [
            r"mypatientvisit\.com",
            r"mynextech\.com"
        ],
        "page_keywords": [
            r"\bmypatientvisit\b",
            r"\bmy patient visit\b",
            r"\bmynextech\b",
            r"\bnextech\b"
        ]
    },
    {
        "name": "Valant (MyIO)",
        "category": "Behavioral Health EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*valant\.io",
            r"valantmed\.com",
            r"valant\.com"
        ],
        "url_regexes": [
            r"valant\.io",
            r"valantmed\.com"
        ],
        "page_keywords": [
            r"\bvalant\b",
            r"\bmyio\b"
        ]
    },
    {
        "name": "TheraNest (Therapy Brands)",
        "category": "Behavioral Health EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*mytheranest\.com",
            r"theranest\.com"
        ],
        "url_regexes": [
            r"mytheranest\.com",
            r"theranest\.com"
        ],
        "page_keywords": [
            r"\btheranest\b",
            r"\bmytheranest\b"
        ]
    },
    {
        "name": "TherapyAppointment",
        "category": "Mental Health Practice Management",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*therapyappointment\.com"
        ],
        "url_regexes": [
            r"therapyappointment\.com"
        ],
        "page_keywords": [
            r"\btherapyappointment\b"
        ]
    },
    {
        "name": "MD-HQ (Cerbo EHR)",
        "category": "Functional & Integrative Medicine EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*\.md-hq\.com",
            r"cerbohealth\.com"
        ],
        "url_regexes": [
            r"\.md-hq\.com"
        ],
        "page_keywords": [
            r"\bmd-hq\b",
            r"\bcerbo\b"
        ]
    },
    {
        "name": "InteliChart Patient Portal",
        "category": "Patient Engagement & EHR Portal",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*intelichart\.com"
        ],
        "url_regexes": [
            r"intelichart\.com"
        ],
        "page_keywords": [
            r"\bintelichart\b"
        ]
    },
    {
        "name": "Medent",
        "category": "Ambulatory EHR & Practice Management",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*medent\.com",
            r"[a-zA-Z0-9\.\-_]*medentmobile\.com",
            r"medentportal\.com"
        ],
        "url_regexes": [
            r"medent\.com",
            r"medentmobile\.com"
        ],
        "page_keywords": [
            r"\bmedent\b"
        ]
    },
    {
        "name": "TDO Software (Endodontic EHR)",
        "category": "Dental & Endodontic Software",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*tdo4endo\.com"
        ],
        "url_regexes": [
            r"tdo4endo\.com"
        ],
        "page_keywords": [
            r"\btdo software\b",
            r"\btdo4endo\b"
        ]
    },
    {
        "name": "Noona (Varian Oncology EHR)",
        "category": "Oncology EHR & Patient Portal",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*noonaclinic\.us",
            r"noona\.varian\.com"
        ],
        "url_regexes": [
            r"noonaclinic\.us",
            r"noona"
        ],
        "page_keywords": [
            r"\bnoona\b"
        ]
    },
    {
        "name": "Meditab IMS Care",
        "category": "Clinical EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*imscare\.com",
            r"meditab\.com"
        ],
        "url_regexes": [
            r"imscare\.com"
        ],
        "page_keywords": [
            r"\bimscare\b",
            r"\bmeditab\b"
        ]
    },
    {
        "name": "MedInformatix",
        "category": "Radiology & Ambulatory EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*medinformatix\.co",
            r"medinformatix\.com"
        ],
        "url_regexes": [
            r"medinformatix"
        ],
        "page_keywords": [
            r"\bmedinformatix\b"
        ]
    },
    {
        "name": "Abbadox (RadNet Radiology Portal)",
        "category": "Radiology Information System (RIS)",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*abbadox\.com"
        ],
        "url_regexes": [
            r"abbadox\.com"
        ],
        "page_keywords": [
            r"\babbadox\b"
        ]
    },
    {
        "name": "MEDITECH (Patient Portal)",
        "category": "Hospital EHR",
        "domain_patterns": [
            r"[a-zA-Z0-9\.\-_]*meditechportal\.",
            r"meditech\.com"
        ],
        "url_regexes": [
            r"meditechportal",
            r"/meditech"
        ],
        "page_keywords": [
            r"\bmeditech\b"
        ]
    }
]

# Keywords that indicate a patient portal link or section on a website
PORTAL_INTENT_KEYWORDS = [
    r"\bpatient portal\b",
    r"\bpatient login\b",
    r"\bpatient-login\b",
    r"\bpatient access\b",
    r"\baccess portal\b",
    r"\bportal login\b",
    r"\bonline portal\b",
    r"\bclient portal\b",
    r"\bmember login\b",
    r"\bmychart\b",
    r"\bmy chart\b",
    r"\bhealow\b",
    r"\bmycw\b",
    r"\bfollowmyhealth\b",
    r"\bfollow my health\b",
    r"\bonpatient\b",
    r"\bpatient sign in\b",
    r"\bpatient sign-in\b",
    r"\baccess patient portal\b",
    r"\bmedical records portal\b",
    r"\bpay my bill / portal\b",
    r"\bpatient gateway\b",
    r"\bmy cs-link\b"
]

# Common subpages to check if portal is not directly linked on the homepage
COMMON_PORTAL_PATHS = [
    "/patient-portal",
    "/patient-portal/",
    "/portal",
    "/portal/",
    "/patients/portal",
    "/patient-login",
    "/patients/patient-portal",
    "/patient-resources/patient-portal",
    "/for-patients/patient-portal",
    "/patients",
    "/patient-resources",
    "/patient-info",
    "/for-patients"
]


def match_ehr_from_url(url: str):
    """
    Checks if a given URL matches any known EHR / Patient Portal domain patterns or regexes.
    Returns EHR name and category or None.
    """
    if not url:
        return None
    
    url_lower = url.lower()
    parsed = urlparse(url_lower)
    domain_and_path = f"{parsed.netloc}{parsed.path}"

    for signature in EHR_SIGNATURES:
        # Check domain regex patterns
        for pattern in signature["domain_patterns"]:
            if re.search(pattern, domain_and_path, re.IGNORECASE):
                return {
                    "name": signature["name"],
                    "category": signature["category"],
                    "match_type": "URL Domain Pattern",
                    "matched_pattern": pattern
                }
        
        # Check URL regexes
        for u_regex in signature.get("url_regexes", []):
            if re.search(u_regex, url_lower, re.IGNORECASE):
                return {
                    "name": signature["name"],
                    "category": signature["category"],
                    "match_type": "URL Keyword Regex",
                    "matched_pattern": u_regex
                }

    return None


def match_ehr_from_text(text: str):
    """
    Checks if text (anchor text, page heading, or badge) matches known EHR regexes using word boundaries.
    """
    if not text:
        return None
    
    text_lower = text.lower()
    for signature in EHR_SIGNATURES:
        for pattern in signature.get("page_keywords", []):
            if re.search(pattern, text_lower, re.IGNORECASE):
                return {
                    "name": signature["name"],
                    "category": signature["category"],
                    "match_type": "Text Regex Match",
                    "matched_pattern": pattern
                }
    return None
