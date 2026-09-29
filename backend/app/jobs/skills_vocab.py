"""Known skills for deterministic job-description parsing.

Each entry is `canonical name: aliases`. Matching is whole-word and case-insensitive.
The user's own profile skills are always added on top, so niche skills still count.
"""

from __future__ import annotations

SKILLS: dict[str, tuple[str, ...]] = {
    # Languages
    "Python": (), "Java": (), "JavaScript": ("js",), "TypeScript": ("ts",), "Go": ("golang",),
    "Rust": (), "C": (), "C++": ("cpp",), "C#": ("csharp",), "Ruby": (), "PHP": (), "Kotlin": (),
    "Swift": (), "Scala": (), "R": (), "Elixir": (), "Erlang": (), "Haskell": (), "Clojure": (),
    "Perl": (), "Dart": (), "Objective-C": (), "Lua": (), "Julia": (), "Bash": ("shell scripting",),
    "SQL": (), "PL/SQL": (), "Solidity": (),
    # Web & frameworks
    "React": ("react.js", "reactjs"), "Next.js": ("nextjs",), "Vue.js": ("vue", "vuejs"),
    "Angular": (), "Svelte": (), "Node.js": ("node", "nodejs"), "Express": ("express.js",),
    "Django": (), "Flask": (), "FastAPI": (), "Spring": ("spring boot",), "Rails": ("ruby on rails",),
    "Laravel": (), ".NET": ("dotnet", "asp.net"), "GraphQL": (), "REST": ("restful", "rest api", "rest apis"),
    "gRPC": (), "HTML": ("html5",), "CSS": ("css3",), "Tailwind CSS": ("tailwind",), "Redux": (),
    "React Native": (), "Flutter": (), "iOS": (), "Android": (), "Electron": (), "WebSockets": ("websocket",),
    # Data & ML
    "PostgreSQL": ("postgres",), "MySQL": (), "SQLite": (), "MongoDB": ("mongo",), "Redis": (),
    "Cassandra": (), "DynamoDB": (), "Elasticsearch": ("elastic search",), "Snowflake": (),
    "BigQuery": (), "Redshift": (), "ClickHouse": (), "Kafka": ("apache kafka",), "RabbitMQ": (),
    "Spark": ("apache spark", "pyspark"), "Hadoop": (), "Airflow": ("apache airflow",), "dbt": (),
    "Pandas": (), "NumPy": (), "scikit-learn": ("sklearn",), "TensorFlow": (), "PyTorch": (),
    "Keras": (), "Machine Learning": ("ml",), "Deep Learning": (), "NLP": ("natural language processing",),
    "Computer Vision": (), "LLMs": ("llm", "large language models"), "Data Engineering": (),
    "Data Analysis": ("data analytics",), "Statistics": (), "Tableau": (), "Power BI": ("powerbi",),
    "Looker": (), "Excel": (), "ETL": (),
    # Cloud & infra
    "AWS": ("amazon web services",), "GCP": ("google cloud", "google cloud platform"),
    "Azure": ("microsoft azure",), "Docker": (), "Kubernetes": ("k8s",), "Terraform": (),
    "Ansible": (), "Helm": (), "Linux": (), "CI/CD": ("ci / cd", "continuous integration"),
    "Jenkins": (), "GitHub Actions": (), "GitLab CI": (), "Git": (), "Prometheus": (), "Grafana": (),
    "Datadog": (), "Nginx": (), "Serverless": (), "Lambda": ("aws lambda",), "Microservices": (),
    "Distributed Systems": (), "System Design": (), "Networking": (), "Security": ("cybersecurity",),
    "OAuth": (), "Celery": (),
    # Practices & product
    "Agile": (), "Scrum": (), "TDD": ("test-driven development",), "Unit Testing": (),
    "Selenium": (), "Playwright": (), "Cypress": (), "Jest": (), "Pytest": (),
    "Product Management": (), "Figma": (), "UX Design": ("ux",), "UI Design": (),
    "Salesforce": (), "SAP": (), "Jira": (),
}  # fmt: skip

# Aliases too ambiguous to trust as whole words in prose ("go" to the store, "r" etc.).
AMBIGUOUS = frozenset({"Go", "C", "R", "REST", "Spring", "Express", "Security", "Lambda", "Excel"})


def _key(value: str) -> str:
    return " ".join(value.casefold().replace(".", " ").split())


_CANONICAL: dict[str, str] = {}
for _name, _aliases in SKILLS.items():
    for _alias in (_name, *_aliases):
        _CANONICAL.setdefault(_key(_alias), _name)


def canonical_skill(name: str) -> str:
    """The vocabulary's name for a skill ("postgres" -> "PostgreSQL"), else `name` itself."""
    return _CANONICAL.get(_key(name), name.strip())
