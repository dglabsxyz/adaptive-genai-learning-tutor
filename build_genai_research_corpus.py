from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


BASE = Path(__file__).resolve().parent / "genai_research"
LAST_RESEARCHED_AT = "2026-06-14T20:03:06Z"

PLATFORM_FOLDERS = {
    "youtube",
    "linkedin",
    "maven",
    "website",
    "github",
    "x",
    "medium",
    "substack",
    "news",
    "podcast",
    "conference",
    "other",
}

FIRECRAWL_CAPABILITIES_DISCOVERED = [
    "firecrawl_search",
    "firecrawl_search_feedback",
    "firecrawl_scrape",
    "firecrawl_extract",
    "firecrawl_map",
    "firecrawl_crawl",
    "firecrawl_check_crawl_status",
    "firecrawl_agent",
    "firecrawl_agent_status",
    "firecrawl_interact",
    "firecrawl_interact_stop",
    "firecrawl_monitor_create",
    "firecrawl_monitor_list",
    "firecrawl_monitor_get",
    "firecrawl_monitor_update",
    "firecrawl_monitor_delete",
    "firecrawl_monitor_run",
    "firecrawl_monitor_checks",
    "firecrawl_monitor_check",
]

SEARCHES_PERFORMED = [
    {
        "query": "Gen AI Academy generative AI courses instructors prompt engineering RAG AI agents Maven YouTube LinkedIn",
        "search_id": "019ec7b1-dcde-7779-b782-031f33aae71c",
        "rating": "good",
    },
    {
        "query": "site:maven.com generative AI course RAG AI agents prompt engineering instructor",
        "search_id": "019ec7b2-101d-702d-ad2b-812f9ff4fee2",
        "rating": "good",
    },
    {
        "query": "site:maven.com RAG Maven course AI instructor",
        "search_id": "019ec7b2-3924-7458-8687-246777918ca1",
        "rating": "good",
    },
    {
        "query": "site:youtube.com generative AI full course prompt engineering RAG AI agents instructor",
        "search_id": "019ec7b4-77f3-719f-ae1f-6afd204bdc51",
        "rating": "good",
    },
    {
        "query": "site:github.com generative-ai-for-beginners llm course rag agents prompt engineering github course",
        "search_id": "019ec7b4-a9e3-7616-89bc-b72dd08bf297",
        "rating": "good",
    },
    {
        "query": "DeepLearning.AI generative AI short courses prompt engineering RAG agents fine tuning evaluation instructors",
        "search_id": "019ec7b4-dd6e-70b3-8e9a-f3b7c75bacdf",
        "rating": "good",
    },
    {
        "query": "site:linkedin.com/learning generative AI prompt engineering RAG AI agents instructor course LinkedIn Learning",
        "search_id": "019ec7b5-11e5-7594-afc1-609f7a41bd76",
        "rating": "good",
    },
    {
        "query": "official generative AI courses prompt engineering RAG AI agents fine tuning evaluation Coursera Google Cloud AWS Hugging Face Udacity",
        "search_id": "019ec7b5-63f2-76ff-b2d2-f8f0666a6c0f",
        "rating": "good",
    },
    {
        "query": "Hugging Face Learn LLM course agents RAG fine tuning evaluation prompt engineering official",
        "search_id": "019ec7b5-a746-7506-8d6e-ddb0c992a1c7",
        "rating": "good",
    },
    {
        "query": "site:huggingface.co/learn agents course AI agents hugging face official",
        "search_id": "019ec7b5-d96a-7646-9f16-6cb44b043ac2",
        "rating": "good",
    },
    {
        "query": "Google Cloud Skills Boost generative AI learning path prompt design image generation course official",
        "search_id": "019ec7b8-253e-741e-be77-94005eec2d54",
        "rating": "good",
    },
    {
        "query": "image generation video generation voice AI multimodal AI courses instructors generative AI Maven YouTube LinkedIn DeepLearning.AI",
        "search_id": "019ec7b8-bbff-778c-b981-280c9dd2f3cb",
        "rating": "good",
    },
    {
        "query": "voice AI course generative AI audio agents speech synthesis instructors official YouTube Maven LinkedIn",
        "search_id": "019ec7b8-f552-712a-844e-45b530af66eb",
        "rating": "good",
    },
    {
        "query": "generative AI RAG agents prompt engineering newsletter Substack Medium podcast conference workshop instructor course",
        "search_id": "019ec7ba-4b41-75ea-b792-76e77627e155",
        "rating": "good",
    },
]


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "unknown"


def uniq(values):
    seen = set()
    out = []
    for value in values or []:
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        key = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
        if key not in seen:
            seen.add(key)
            out.append(value)
    return out


def platform_folder(platform: str | None = None, url: str | None = None) -> str:
    text = f"{platform or ''} {url or ''}".lower()
    if "youtube.com" in text or "youtu.be" in text or "youtube" in text:
        return "youtube"
    if "linkedin.com" in text or "linkedin" in text:
        return "linkedin"
    if "maven.com" in text or "maven" in text:
        return "maven"
    if "github.com" in text or "github" in text:
        return "github"
    if "twitter.com" in text or "x.com" in text:
        return "x"
    if "medium.com" in text or "medium" in text:
        return "medium"
    if "substack.com" in text or "substack" in text:
        return "substack"
    if "podcast" in text:
        return "podcast"
    if "goto" in text or "conference" in text or "neurips" in text or "icml" in text:
        return "conference"
    if "news" in text or "blog" in text:
        return "news"
    if any(
        domain in text
        for domain in [
            "deeplearning.ai",
            "huggingface.co",
            "skills.google",
            "coursera.org",
            "udacity.com",
            "learn.microsoft.com",
            "fast.ai",
            "runwayml.com",
            "datacamp.com",
            "harvard.edu",
            "mit.edu",
            "anthropic.com",
            "openai.com",
        ]
    ):
        return "website"
    return "other"


def record(platform, url, title, summary, content_type="course", extracted_data=None):
    return {
        "platform": platform,
        "url": url,
        "title": title,
        "summary": summary,
        "content_type": content_type,
        "extracted_data": extracted_data or {},
        "citations": [url] if url else [],
    }


def parse_price(raw):
    raw = None if raw == "" else raw
    if raw is None:
        return {"amount": None, "currency": None, "raw": None}
    text = str(raw).strip()
    if not text:
        return {"amount": None, "currency": None, "raw": None}
    if text.lower() == "free":
        return {"amount": 0, "currency": "USD", "raw": text}
    match = re.search(r"\$([0-9][0-9,]*(?:\.[0-9]+)?)", text)
    if match:
        return {"amount": float(match.group(1).replace(",", "")), "currency": "USD", "raw": text}
    return {"amount": None, "currency": None, "raw": text}


def parse_rating(raw):
    raw = None if raw == "" else raw
    if raw is None:
        return {"value": None, "count": None, "raw": None}
    text = str(raw).strip()
    if not text:
        return {"value": None, "count": None, "raw": None}
    value_match = re.search(r"([0-5](?:\.[0-9])?)", text)
    count_match = re.search(r"\(([\d,]+)\)", text)
    return {
        "value": float(value_match.group(1)) if value_match else None,
        "count": int(count_match.group(1).replace(",", "")) if count_match else None,
        "raw": text,
    }


def course(
    name,
    instructors,
    platform,
    url,
    tags,
    description,
    *,
    syllabus=None,
    audience=None,
    prerequisites=None,
    duration=None,
    format_=None,
    price=None,
    rating=None,
    certificate=None,
    enrollment_status=None,
    last_updated=None,
    organization=None,
    citations=None,
    source_title=None,
    source_summary=None,
    content_type="course",
    entity_type="course",
):
    source_title = source_title or name
    source_summary = source_summary or description
    all_citations = uniq([url] + (citations or []))
    return {
        "entity_type": entity_type,
        "course_name": name,
        "course_slug": slugify(name),
        "instructor_names": instructors or [],
        "platform": platform,
        "course_url": url,
        "topic_tags": tags or [],
        "description": description,
        "syllabus": syllabus or [],
        "target_audience": audience or [],
        "prerequisites": prerequisites or [],
        "duration": duration,
        "format": format_,
        "price_raw": price,
        "rating_raw": rating,
        "certificate": certificate,
        "enrollment_status": enrollment_status,
        "last_updated": last_updated,
        "organization": organization,
        "citations": all_citations,
        "source_records": [
            record(platform, url, source_title, source_summary, content_type, {"entity_type": entity_type})
        ],
    }


TOPICS = [
    {
        "topic": "LLMs",
        "description": "Large language model fundamentals, transformer-based models, tokenization, inference, deployment, and LLM application patterns.",
        "related_topics": ["prompt engineering", "fine-tuning", "RAG", "AI agents", "context engineering"],
        "sources": [
            "https://huggingface.co/learn/llm-course/en/chapter1/1",
            "https://www.deeplearning.ai/courses/generative-ai-with-llms",
        ],
        "keywords": ["llm", "large language", "transformer", "language model", "nlp"],
    },
    {
        "topic": "prompt engineering",
        "description": "Designing instructions, examples, context, and output constraints to guide generative models toward useful results.",
        "related_topics": ["LLMs", "context engineering", "AI agents", "RAG", "AI coding"],
        "sources": [
            "https://www.linkedin.com/learning/introduction-to-prompt-engineering-for-generative-ai-24636124",
            "https://github.com/dair-ai/Prompt-Engineering-Guide",
            "https://github.com/anthropics/prompt-eng-interactive-tutorial",
        ],
        "keywords": ["prompt", "prompting"],
    },
    {
        "topic": "RAG",
        "description": "Retrieval-augmented generation systems that ground model output in external corpora, search, embeddings, and vector databases.",
        "related_topics": ["LLMs", "vector databases", "embeddings", "AI agents", "AI evaluation"],
        "sources": [
            "https://www.deeplearning.ai/courses/retrieval-augmented-generation",
            "https://maven.com/applied-llms/rag-playbook",
            "https://maven.com/alexey-grigorev/from-rag-to-agents",
        ],
        "keywords": ["rag", "retrieval", "vector", "embedding", "search"],
    },
    {
        "topic": "AI agents",
        "description": "Systems that use models, tools, memory, planning, orchestration, and evaluation to complete multi-step goals.",
        "related_topics": ["LLMs", "tool use", "RAG", "multi-agent systems", "AI automation"],
        "sources": [
            "https://huggingface.co/learn/agents-course/unit0/introduction",
            "https://github.com/microsoft/ai-agents-for-beginners",
            "https://maven.com/aishwarya-srinivasan/mastering-ai-agents",
        ],
        "keywords": ["agent", "agentic", "multi-agent", "tool use", "langgraph", "crewai"],
    },
    {
        "topic": "fine-tuning",
        "description": "Adapting foundation models with supervised fine-tuning, PEFT, LoRA/QLoRA, RLHF-style techniques, and evaluation.",
        "related_topics": ["LLMs", "model customization", "datasets", "AI safety and evaluation"],
        "sources": [
            "https://www.deeplearning.ai/courses/generative-ai-with-llms",
            "https://www.linkedin.com/learning/fine-tuning-for-llms-from-beginner-to-advanced",
            "https://huggingface.co/learn/llm-course/en/chapter1/1",
        ],
        "keywords": ["fine-tun", "finetun", "lora", "qlora", "rlhf", "customiz"],
    },
    {
        "topic": "multimodal AI",
        "description": "Models and applications that combine text, image, video, audio, and other modalities.",
        "related_topics": ["image generation", "video generation", "voice AI", "RAG", "prompt engineering"],
        "sources": [
            "https://www.linkedin.com/learning/multimodal-ai-essentials-merging-text-image-and-audio-for-next-generation-ai-applications",
            "https://www.deeplearning.ai/courses/ai-agents-for-image-and-video-generation",
            "https://www.skills.google/course_templates/976",
        ],
        "keywords": ["multimodal", "image analysis", "audio", "video", "vision"],
    },
    {
        "topic": "image generation",
        "description": "Creating and editing images with diffusion models, text-to-image systems, and creative AI workflows.",
        "related_topics": ["diffusion models", "multimodal AI", "video generation", "prompt engineering"],
        "sources": [
            "https://www.deeplearning.ai/courses/ai-agents-for-image-and-video-generation",
            "https://maven.com/bilawal/generative-ai-masterclass",
            "https://huggingface.co/learn",
        ],
        "keywords": ["image generation", "text-to-image", "diffusion", "midjourney", "dall-e", "stable diffusion"],
    },
    {
        "topic": "video generation",
        "description": "Generating, editing, evaluating, and orchestrating AI-created video.",
        "related_topics": ["image generation", "multimodal AI", "generative media", "voice AI"],
        "sources": [
            "https://www.deeplearning.ai/courses/ai-agents-for-image-and-video-generation",
            "https://academy.runwayml.com/",
            "https://maven.com/bilawal/generative-ai-masterclass",
        ],
        "keywords": ["video generation", "text-to-video", "ai video", "runway", "generative media"],
    },
    {
        "topic": "voice AI",
        "description": "Speech-to-text, text-to-speech, voice cloning, real-time voice agents, and audio generation workflows.",
        "related_topics": ["AI agents", "multimodal AI", "conversation design", "audio AI"],
        "sources": [
            "https://maven.com/p/5de0a6/become-a-voice-ai-agent-expert",
            "https://www.linkedin.com/learning/elevenlabs-ai-voice-cloning-text-to-speech-and-sound-effects",
            "https://www.youtube.com/watch?v=m4QF78X7t9k",
        ],
        "keywords": ["voice", "speech", "tts", "stt", "audio", "elevenlabs"],
    },
    {
        "topic": "AI coding",
        "description": "AI-assisted software development with coding agents, Copilot, Cursor, Claude Code, Codex-style workflows, and AI prototyping.",
        "related_topics": ["AI agents", "vibe coding", "AI product development", "prompt engineering"],
        "sources": [
            "https://maven.com/courses/ai/ai-coding",
            "https://maven.com/courses/ai/vibe-coding",
            "https://learn.microsoft.com/en-us/training/paths/get-started-ai-apps-agents/",
        ],
        "keywords": ["coding", "code", "claude code", "cursor", "copilot", "vibe"],
    },
    {
        "topic": "AI product development",
        "description": "Building AI products from opportunity discovery and prototyping through evaluation, launch, and iteration.",
        "related_topics": ["AI product management", "AI coding", "AI agents", "business AI"],
        "sources": [
            "https://maven.com/mahesh-yadav/genaipm",
            "https://maven.com/product-faculty/ai-product-management-certification",
            "https://maven.com/courses/ai/prototyping",
        ],
        "keywords": ["product", "pm", "prototype", "mvp", "build"],
    },
    {
        "topic": "AI automation",
        "description": "Workflow automation using LLMs, agents, APIs, no-code platforms, and orchestration tools such as Zapier, n8n, and Make.",
        "related_topics": ["AI agents", "no-code AI", "business AI", "voice AI"],
        "sources": [
            "https://maven.com/lennon/ai-agents-for-content",
            "https://www.coursera.org/learn/operationalizing-no-code-ai-with-zapier-automation-and-plans",
            "https://startup-sync.com/ai-automation-integration-course/",
        ],
        "keywords": ["automation", "workflow", "zapier", "n8n", "make", "operations"],
    },
    {
        "topic": "business AI",
        "description": "Executive, operator, marketing, sales, and transformation uses of AI, including ROI and organizational adoption.",
        "related_topics": ["AI automation", "AI product development", "enterprise AI", "AI agents"],
        "sources": [
            "https://maven.com/ai-agent-campus/ai-agents-for-sales-and-go-to-market",
            "https://professional.dce.harvard.edu/programs/ai-strategy-for-business-leaders/",
            "https://executive.mit.edu/course/artificial-intelligence/a056g00000URaa3AAD.html",
        ],
        "keywords": ["business", "sales", "gtm", "marketing", "leader", "strategy", "roi"],
    },
    {
        "topic": "no-code AI",
        "description": "Building AI products and automations with visual builders, workflow platforms, and natural-language development tools.",
        "related_topics": ["AI automation", "AI coding", "AI product development", "business AI"],
        "sources": [
            "https://maven.com/no-code-ai/vibe-coding-bootcamp",
            "https://www.coursera.org/learn/operationalizing-no-code-ai-with-zapier-automation-and-plans",
            "https://zapier.com/blog/no-code-automation/",
        ],
        "keywords": ["no-code", "low-code", "lovable", "replit", "zapier", "visual"],
    },
    {
        "topic": "AI safety and evaluation",
        "description": "Model/application evaluation, red-teaming, responsible AI, trustworthy AI, safety, bias, and production readiness.",
        "related_topics": ["AI evals", "responsible AI", "AI agents", "RAG", "fine-tuning"],
        "sources": [
            "https://maven.com/parlance-labs/evals",
            "https://www.skills.google/paths/118/course_templates/554",
            "https://www.coursera.org/learn/responsible-ai-and-ethics",
        ],
        "keywords": ["eval", "evaluation", "safety", "responsible", "ethics", "bias", "red-team", "trustworthy"],
    },
    {
        "topic": "context engineering",
        "description": "Designing context, retrieval, memory, tool outputs, and constraints around model calls for reliable AI systems.",
        "related_topics": ["prompt engineering", "RAG", "AI agents", "LLMs"],
        "sources": [
            "https://www.linkedin.com/learning/context-engineering-for-developers",
            "https://huggingface.co/learn",
            "https://maven.com/aishwarya-srinivasan/mastering-ai-agents",
        ],
        "keywords": ["context", "memory", "retrieval"],
    },
    {
        "topic": "MCP",
        "description": "Model Context Protocol patterns for connecting AI agents and applications to tools, data sources, and local/remote capabilities.",
        "related_topics": ["AI agents", "AI coding", "context engineering", "tool use"],
        "sources": [
            "https://maven.com/courses/ai/mcp",
            "https://alexeyondata.substack.com/p/11-workshops-to-build-production",
        ],
        "keywords": ["mcp", "model context protocol"],
    },
]


COURSES = [
    course(
        "Mastering Agentic AI: Certification by The Gen Academy",
        ["Aishwarya Srinivasan", "Arvind Narayanamurthy"],
        "Maven",
        "https://maven.com/aishwarya-srinivasan/mastering-ai-agents",
        ["AI agents", "RAG", "fine-tuning", "AI evals", "AI safety and evaluation"],
        "A six-week Maven program from The Gen Academy on building and deploying robust agentic AI systems.",
        syllabus=[
            "Gen AI Building Blocks",
            "Grounding AI with RAG and Context Engineering",
            "The Agentic Leap",
            "Finetuning and Local Models",
            "AI Evals, Security and Production Readiness",
            "AI Career Launchpad and becoming AI-native",
        ],
        audience=["Engineers", "PMs", "Data scientists/analysts", "Leaders", "Entrepreneurs", "Future AI practitioners"],
        prerequisites=["No coding background required", "No prior AI experience needed"],
        duration="6 weeks",
        format_="Cohort-based course",
        price="$2,499",
        certificate="The Gen Academy certificate issued upon completing the program",
        enrollment_status="Available",
        organization="The Gen Academy",
    ),
    course(
        "AI Engineering Buildcamp: From RAG to Agents",
        ["Alexey Grigorev"],
        "Maven",
        "https://maven.com/alexey-grigorev/from-rag-to-agents",
        ["RAG", "AI agents", "LLMs", "AI engineering", "search"],
        "Create your own production-ready AI application in six weeks.",
        syllabus=[
            "Course overview and logistics",
            "Environment preparation",
            "Foundation: LLMs, RAG and search",
            "Structured output",
            "Project work",
            "Homework",
            "RAG use-cases overview",
        ],
        audience=["Data scientists and ML engineers", "Software engineers", "AI enthusiasts"],
        prerequisites=["Coding", "Python", "Git", "Docker", "OpenAI key or alternative"],
        duration="6 weeks",
        format_="Cohort-based course",
        price="$1,799",
        rating="4.5 (21)",
        certificate="Certificate of completion",
        enrollment_status="Next cohort: Sep 21-Nov 22, 2026",
        organization="DataTalks.Club",
    ),
    course(
        "Systematically Improving RAG Applications",
        ["Jason Liu"],
        "Maven",
        "https://maven.com/applied-llms/rag-playbook",
        ["RAG", "AI evaluation", "retrieval", "multimodal AI"],
        "A repeatable process for evaluating and improving RAG applications.",
        syllabus=[
            "Evaluate retrieval quality using precision, recall, and MRR",
            "Create evaluation datasets using LLMs",
            "Develop multimodal retrieval systems",
            "Extract structured information from diverse data sources",
        ],
        audience=["Product leaders", "Engineers", "Data scientists"],
        prerequisites=["Deployed a RAG system", "Optional Python"],
        format_="Cohort-based course",
        rating="4.8 (87)",
        certificate="Certificate of completion",
        organization="Applied LLMs",
    ),
    course(
        "Search in the LLM Era for AI Engineers",
        ["Nirant Kasliwal", "Jithin James", "Dhruv Anand"],
        "Maven",
        "https://maven.com/nirantk/search-for-rag",
        ["RAG", "search", "vector databases", "AI evaluation", "multimodal AI"],
        "A six-weekend instructor-led course and live practice for senior engineers building modern search and RAG systems.",
        syllabus=[
            "Finding and measuring hallucinations with Ragas",
            "Query understanding and profiling",
            "Testset generation and LLM-as-judge with Ragas",
            "Parsing, chunking and metadata enrichment",
            "Embedding models",
            "Reducing LLM latency and improving throughput",
            "Scaling dense retrieval",
            "Vector databases and search engines",
            "Semi-structured multimodal RAG",
            "Structured information extraction",
        ],
        audience=["Senior data scientists", "ML engineers", "CTOs", "Technical leaders"],
        prerequisites=["RAG architecture", "RAG evaluation metrics", "Embedding models and vector databases"],
        duration="6 weeks",
        format_="Instructor-led course",
        certificate="Certificate of completion",
    ),
    course(
        "AI Evals For Engineers and PMs",
        ["Hamel Husain", "Shreya Shankar"],
        "Maven",
        "https://maven.com/parlance-labs/evals",
        ["AI safety and evaluation", "AI agents", "AI product development", "RAG"],
        "Build a real AI agent, find where it breaks, and improve it with evals you can trust.",
        syllabus=[
            "Building agents: foundations",
            "Designing for evaluability",
            "Error analysis and finding failures",
            "Building trusted evaluators",
            "Catch regressions with CI/CD",
            "Red-team for safety",
            "Improve accuracy and cut cost with evidence",
        ],
        audience=["Engineers", "Product managers", "AI developers"],
        prerequisites=["Familiarity with AI applications", "Basic understanding of how LLMs work"],
        duration="4 weeks",
        format_="Cohort-based course",
        price="$4,200",
        rating="4.7",
        certificate="Certificate of completion",
        enrollment_status="Open",
        organization="Parlance Labs",
    ),
    course(
        "Build Production AI Agents for 10x-100x ROI",
        ["Dr Ankur Narang", "Kush Khurana", "Dr Aveek Brahmachari"],
        "Maven",
        "https://maven.com/deep-core-x-academy/production-ai-agents",
        ["AI agents", "RAG", "business AI", "production AI"],
        "A Maven course on leaving with deployable production agent systems and documented architecture.",
        syllabus=["Foundations and structured action", "Retrieval and grounding"],
        audience=["Engineering and product leaders", "Technical founders and CTOs", "Lead developers"],
        prerequisites=["Python proficiency", "Familiarity with APIs and basic software engineering"],
        duration="4 weeks",
        format_="Cohort-based course",
        price="$1,200",
        certificate="Certificate of completion",
        enrollment_status="Next cohort: July 7-Aug 1, 2026",
        organization="DeepCoreX Academy",
    ),
    course(
        "AI Agents for Sales and GTM",
        ["John Hwang"],
        "Maven",
        "https://maven.com/ai-agent-campus/ai-agents-for-sales-and-go-to-market",
        ["AI agents", "business AI", "AI automation", "sales", "marketing"],
        "Build AI employees that scale marketing, streamline sales, and increase profits.",
        syllabus=["AI-native sales and marketing overview", "AI agents crash course", "AI agents for knowledge management"],
        audience=["Sales and marketing professionals", "High-ticket consultancies", "Lead generation and marketing agencies"],
        prerequisites=["Basic technical fluency with APIs and webhooks", "Some familiarity with AI and prompting"],
        duration="3 weeks",
        format_="Cohort-based course",
        certificate="Certificate of completion",
    ),
    course(
        "AI Mini-Bootcamp",
        ["Sheamus McGovern"],
        "Maven",
        "https://maven.com/aitraining/minibootcamp",
        ["LLMs", "RAG", "AI agents", "AI automation", "AI product development"],
        "A six-week pre-conference live and on-demand training program for AI fundamentals.",
        syllabus=[
            "AI and Machine Learning Foundations",
            "AI and Machine Learning Modeling",
            "Data prep for Machine Learning and LLMs with Python",
            "Introduction to LLMs",
            "Building knowledge-grounded LLMs with RAG",
            "Introduction to AI Agents",
            "Automating workflows with Agentic AI",
            "Capstone: build and deploy your agentic AI application",
        ],
        audience=["AI novices", "Software engineers", "Product managers", "Builders"],
        prerequisites=["None"],
        duration="6 weeks",
        format_="Bootcamp",
        rating="4.6",
        certificate="Certificate of completion",
        enrollment_status="Open",
        organization="AI+ Training and Agentic AI Summit",
        entity_type="bootcamp",
    ),
    course(
        "AI Agents for Content Creators",
        ["Rob Lennon"],
        "Maven",
        "https://maven.com/lennon/ai-agents-for-content",
        ["AI agents", "AI automation", "business AI", "content creation"],
        "A blueprint for using AI agents to source ideas, draft emails, and write posts in a creator's style and point of view.",
        syllabus=[
            "Listeners: the inspiration engine",
            "Writers: email and social co-writers",
            "Simple and templated automation and workflow agents",
            "Live calls to implement the system",
        ],
        audience=["Content creators", "Coaches", "Course sellers", "Solo entrepreneurs", "Marketers"],
        duration="10 days",
        format_="Cohort-based course",
        price="$475",
        rating="4.8",
        certificate="Certificate of completion",
        enrollment_status="Open",
    ),
    course(
        "AI Agent Engineering: From ReAct, Agentic RAG to Multi-Agent Orchestration",
        ["Rakesh Gohel"],
        "Maven",
        "https://maven.com/rakeshgohel/ai-agent-engineering-react-rag-multi-agent",
        ["AI agents", "RAG", "multi-agent systems", "enterprise AI"],
        "Design, deploy, and scale enterprise-grade AI agents with a hands-on, problem-driven approach.",
        syllabus=[
            "Foundations: concepts of a true agentic system in enterprise",
            "Agentic RAG systems and multi-agent workflows",
        ],
        audience=["Technical architects", "Data scientists", "Product managers", "AI solution strategists", "Tech leads", "Backend developers"],
        prerequisites=["Python proficiency", "Basic concepts of language models", "Software engineering principles"],
        format_="Cohort-based course",
        rating="4.8 (24)",
        certificate="Certificate of completion",
        organization="JUTEQ Inc.",
    ),
    course(
        "Agentic AI Product Management Certification using Claude Code",
        ["Mahesh Yadav"],
        "Maven",
        "https://maven.com/mahesh-yadav/genaipm",
        ["AI product development", "AI agents", "RAG", "AI coding", "Claude Code"],
        "A certification for leading agentic AI products, building systems, defining metrics, and scaling responsibly.",
        syllabus=[
            "AI PM skills and ecosystems",
            "ML concepts",
            "Hands-on lab",
            "Action items",
            "Optional ML concept lessons",
            "Build in public",
        ],
        audience=["Product managers", "Consultants", "Data scientists", "Designers", "Program/project managers", "Engineers"],
        duration="8 hrs/week",
        format_="Certification course",
        price="$3,000",
        rating="4.8 (533)",
        certificate="Yes",
        enrollment_status="Open",
        organization="Agentic AI Institute",
    ),
    course(
        "Generative AI Creation Masterclass",
        ["Bilawal Sidhu"],
        "Maven",
        "https://maven.com/bilawal/generative-ai-masterclass",
        ["image generation", "video generation", "voice AI", "multimodal AI", "generative media"],
        "A creative GenAI workflow masterclass covering text, image, audio, video, and 3D generation.",
        syllabus=[
            "Navigating the generative AI landscape",
            "Creative fusion: multimodal AI creation workflows",
            "Capstone project and guest speaker John Nack",
        ],
        audience=["Creative professionals", "Managers or executives", "Curious hobbyists"],
        duration="10 days",
        format_="Masterclass",
        rating="4.7",
    ),
    course(
        "Become a Voice AI Agent Expert",
        ["Kwindla Hultman Kramer"],
        "Maven",
        "https://maven.com/p/5de0a6/become-a-voice-ai-agent-expert",
        ["voice AI", "AI agents", "AI automation", "speech-to-text", "text-to-speech"],
        "A Maven lesson on voice agent building blocks, models, latency, hosting, telephony, and evaluation.",
        syllabus=[
            "Introduction to Pipecat and resources",
            "Voice AI growth and use cases",
            "Defining a voice agent and core challenges",
            "Three-model architecture of voice AI",
            "Latency in voice AI",
            "Models for STT, LLM and TTS",
            "WebRTC vs WebSockets and telephony basics",
            "Evals, scaling and advanced workflows",
            "Human-like turn detection",
            "Speech-to-speech, video and on-device models",
        ],
        audience=["Students", "Professionals", "Tech enthusiasts"],
        format_="Lesson",
        price="Free",
        enrollment_status="Open",
        content_type="other",
        entity_type="teaching resource",
    ),
    course(
        "AI Prototyping for Designers",
        ["Anna Arteeva"],
        "Maven",
        "https://maven.com/anna-arteeva/prototyping-for-designers",
        ["AI product development", "AI coding", "no-code AI", "multimodal AI"],
        "A Maven AI prototyping course found in the Maven AI prototyping catalog crawl.",
        audience=["Designers", "Product designers", "Product teams"],
        format_="Cohort-based course",
        rating="4.8",
        citations=["https://maven.com/courses/ai/prototyping"],
    ),
    course(
        "Vibe Coding Bootcamp",
        ["No-Code AI"],
        "Maven",
        "https://maven.com/no-code-ai/vibe-coding-bootcamp",
        ["AI coding", "no-code AI", "AI product development"],
        "A Maven AI/vibe-coding course discovered from the Maven prototyping and vibe-coding category crawls.",
        audience=["Non-technical builders", "Product teams", "Founders"],
        format_="Bootcamp",
        citations=["https://maven.com/courses/ai/vibe-coding", "https://maven.com/courses/ai/prototyping"],
        entity_type="bootcamp",
    ),
    course(
        "AI Product Management Certification",
        ["Product Faculty"],
        "Maven",
        "https://maven.com/product-faculty/ai-product-management-certification",
        ["AI product development", "business AI"],
        "A Maven AI product management certification discovered in the Maven AI catalog crawl.",
        audience=["Product managers", "Product leaders"],
        format_="Certification course",
        citations=["https://maven.com/courses/ai"],
    ),
    course(
        "AI Software Development: From First Prompt to Production Code",
        ["Maven instructors"],
        "Maven",
        "https://maven.com/courses/ai/ai-coding",
        ["AI coding", "AI agents", "AI product development"],
        "A Maven AI coding catalog entry described as a four-week, highly rated course from first prompt to production code.",
        duration="4 weeks",
        format_="Course",
        rating="4.9",
        citations=["https://maven.com/courses/ai/ai-coding"],
    ),
    course(
        "AI Agents Course",
        ["Ben Burtenshaw", "Sergio Paniego"],
        "Hugging Face",
        "https://huggingface.co/learn/agents-course/unit0/introduction",
        ["AI agents", "LLMs", "tool use", "LangGraph", "LlamaIndex", "smolagents", "AI safety and evaluation"],
        "A free Hugging Face course from beginner to expert on understanding, using, and building AI agents.",
        syllabus=[
            "Onboarding",
            "Agent fundamentals",
            "Frameworks",
            "Use cases",
            "Final assignment",
            "Fine-tuning an LLM for function calling",
            "Agent observability and evaluation",
            "Agents in games",
        ],
        audience=["Beginners", "AI enthusiasts", "Students interested in AI agents"],
        prerequisites=["Basic Python", "Basic knowledge of LLMs"],
        duration="Approximately 3-4 hours of work per week",
        format_="Online course",
        price="Free",
        certificate="Certificate of completion available",
        organization="Hugging Face",
    ),
    course(
        "LLM Course",
        [
            "Abubakar Abid",
            "Ben Burtenshaw",
            "Matthew Carrigan",
            "Lysandre Debut",
            "Sylvain Gugger",
            "Dawood Khan",
            "Merve Noyan",
            "Lucile Saulnier",
            "Lewis Tunstall",
            "Leandro von Werra",
        ],
        "Hugging Face",
        "https://huggingface.co/learn/llm-course/en/chapter1/1",
        ["LLMs", "NLP", "Transformers", "fine-tuning"],
        "A Hugging Face course on large language models and NLP using libraries from the Hugging Face ecosystem.",
        syllabus=[
            "Introduction to Transformers",
            "Basics of datasets",
            "Basics of tokenizers",
            "Classic NLP tasks",
            "LLM techniques",
            "Building and sharing demos",
            "Advanced LLM topics",
            "Fine-tuning",
            "Curating high-quality datasets",
            "Building reasoning models",
        ],
        audience=["Developers", "Data scientists", "Machine learning engineers"],
        prerequisites=["Good knowledge of Python", "Some familiarity with deep learning"],
        duration="6-8 hours per week for approximately 12 weeks",
        format_="Online course",
        price="Free",
        certificate="Currently no certification available",
        organization="Hugging Face",
    ),
    course(
        "Diffusion Course",
        ["Hugging Face Team"],
        "Hugging Face",
        "https://huggingface.co/learn",
        ["image generation", "diffusion models", "multimodal AI"],
        "A Hugging Face learning catalog course on diffusion models and image-generation workflows.",
        format_="Online course",
        price="Free",
        organization="Hugging Face",
        citations=["https://huggingface.co/learn"],
    ),
    course(
        "Context Course",
        ["Hugging Face Team"],
        "Hugging Face",
        "https://huggingface.co/learn",
        ["context engineering", "LLMs", "AI coding", "prompt engineering"],
        "A Hugging Face learning catalog course on context engineering for code and AI workflows.",
        format_="Online course",
        price="Free",
        organization="Hugging Face",
        citations=["https://huggingface.co/learn"],
    ),
    course(
        "Generative AI with Large Language Models",
        ["Antje Barth", "Chris Fregly", "Shelbee Eigenbrode", "Mike Chambers"],
        "DeepLearning.AI",
        "https://www.deeplearning.ai/courses/generative-ai-with-llms",
        ["LLMs", "fine-tuning", "AI safety and evaluation", "generative AI"],
        "A DeepLearning.AI course on the generative AI lifecycle, transformer architecture, training, tuning, inference, and LLM-powered applications.",
        syllabus=[
            "Generative AI use cases, project lifecycle, and model pre-training",
            "Fine-tuning and evaluating large language models",
            "Reinforcement learning and LLM-powered applications",
        ],
        audience=["Data scientists", "Machine learning engineers", "Prompt engineers", "Research engineers"],
        prerequisites=["Python coding experience", "Machine learning basics"],
        duration="10h18m",
        format_="Online course",
        price="$49/month",
        certificate="Earn a certificate with PRO",
        enrollment_status="Open",
        organization="DeepLearning.AI",
        citations=["https://www.coursera.org/learn/generative-ai-with-llms"],
    ),
    course(
        "Retrieval Augmented Generation (RAG)",
        ["Zain Hasan"],
        "DeepLearning.AI",
        "https://www.deeplearning.ai/courses/retrieval-augmented-generation",
        ["RAG", "LLMs", "vector databases", "AI safety and evaluation"],
        "A DeepLearning.AI course on designing, building, deploying, and evaluating production-ready RAG applications.",
        syllabus=[
            "RAG overview",
            "Information retrieval and search foundations",
            "Information retrieval with vector databases",
            "LLMs and text generation",
            "RAG systems in production",
        ],
        audience=["Intermediate learners", "AI engineers", "Data scientists"],
        prerequisites=["Intermediate Python", "Basic knowledge of generative AI", "High-school-level math"],
        duration="24h33m",
        format_="Online course",
        certificate="Earn a certificate with PRO",
        enrollment_status="Open",
        organization="DeepLearning.AI",
        citations=["https://www.coursera.org/learn/retrieval-augmented-generation-rag"],
    ),
    course(
        "AI Agents for Image and Video Generation",
        ["Katie Nguyen", "Wafae Bakkali"],
        "DeepLearning.AI",
        "https://www.deeplearning.ai/courses/ai-agents-for-image-and-video-generation",
        ["AI agents", "image generation", "video generation", "multimodal AI", "AI safety and evaluation"],
        "A DeepLearning.AI course on building media agents that generate, evaluate, and iterate on image and video outputs.",
        syllabus=[
            "Overview of generative media",
            "Prompt engineering for image generation",
            "Prompt engineering for video generation",
            "Evaluation techniques",
            "Image generation agent",
            "Video generation agent",
            "Building media agent with AI",
        ],
        audience=["AI builders", "Developers", "Data scientists"],
        prerequisites=["Familiarity with Python", "Basic experience working with LLM APIs"],
        duration="1h24m",
        format_="Short course",
        certificate="Earn an accomplishment with PRO",
        enrollment_status="Open",
        organization="Google",
    ),
    course(
        "Generative AI for Everyone",
        ["Andrew Ng"],
        "DeepLearning.AI",
        "https://www.deeplearning.ai/courses/generative-ai-for-everyone",
        ["LLMs", "business AI", "generative AI", "AI product development"],
        "A DeepLearning.AI course by Andrew Ng about how generative AI works, what it can do, and how to use it in work and business.",
        format_="Online course",
        organization="DeepLearning.AI",
    ),
    course(
        "Microsoft Generative AI for Beginners",
        ["Microsoft Cloud Advocates"],
        "GitHub",
        "https://github.com/microsoft/generative-ai-for-beginners",
        ["LLMs", "prompt engineering", "RAG", "AI safety and evaluation", "AI agents"],
        "A Microsoft open-source curriculum with 21 lessons on building generative AI applications.",
        format_="Open-source curriculum",
        price="Free",
        organization="Microsoft",
        content_type="repository",
        entity_type="teaching resource",
    ),
    course(
        "Microsoft AI Agents for Beginners",
        ["Microsoft"],
        "GitHub",
        "https://github.com/microsoft/ai-agents-for-beginners",
        ["AI agents", "tool use", "multi-agent systems", "AI safety and evaluation"],
        "A Microsoft open-source course with lessons covering the fundamentals of building AI agents.",
        format_="Open-source curriculum",
        price="Free",
        organization="Microsoft",
        content_type="repository",
        entity_type="teaching resource",
    ),
    course(
        "Prompt Engineering Guide",
        ["DAIR.AI"],
        "GitHub",
        "https://github.com/dair-ai/Prompt-Engineering-Guide",
        ["prompt engineering", "context engineering", "AI agents"],
        "A public prompt engineering guide and course-style resource for prompting, context engineering, and AI agents.",
        format_="Guide and learning resource",
        price="Free",
        organization="DAIR.AI",
        content_type="repository",
        entity_type="teaching resource",
    ),
    course(
        "The Large Language Model Course",
        ["Maxime Labonne"],
        "Hugging Face",
        "https://huggingface.co/blog/mlabonne/llm-course",
        ["LLMs", "fine-tuning", "RAG", "AI agents"],
        "A Hugging Face blog/course resource collecting topics and roadmaps for getting into LLMs.",
        format_="Course roadmap",
        price="Free",
        content_type="article",
        entity_type="teaching resource",
    ),
    course(
        "Prompt Engineering Interactive Tutorial",
        ["Anthropic Team"],
        "GitHub",
        "https://github.com/anthropics/prompt-eng-interactive-tutorial",
        ["prompt engineering", "Claude", "LLMs"],
        "An Anthropic interactive tutorial for practicing prompt engineering with Claude.",
        format_="Interactive tutorial",
        price="Free",
        organization="Anthropic",
        citations=["https://www.anthropic.com/learn"],
        content_type="repository",
        entity_type="teaching resource",
    ),
    course(
        "OpenAI Cookbook",
        ["OpenAI"],
        "GitHub",
        "https://github.com/openai/openai-cookbook",
        ["LLMs", "RAG", "AI agents", "fine-tuning", "AI safety and evaluation"],
        "OpenAI's public collection of examples and guides for building with OpenAI models and APIs.",
        format_="Cookbook and examples",
        price="Free",
        organization="OpenAI",
        citations=["https://developers.openai.com/cookbook"],
        content_type="repository",
        entity_type="teaching resource",
    ),
    course(
        "Introduction to Prompt Engineering for Generative AI",
        ["Ronnie Sheer"],
        "LinkedIn Learning",
        "https://www.linkedin.com/learning/introduction-to-prompt-engineering-for-generative-ai-24636124",
        ["prompt engineering", "LLMs", "generative AI"],
        "A LinkedIn Learning course on crafting prompts for Copilot, ChatGPT, Gemini, and Claude.",
        duration="1h 3m",
        format_="Video course",
        price="LinkedIn Premium",
        citations=["https://www.linkedin.com/learning/topics/artificial-intelligence"],
    ),
    course(
        "Hands-On AI: RAG using LlamaIndex",
        ["LinkedIn Learning Team"],
        "LinkedIn Learning",
        "https://www.linkedin.com/learning/hands-on-ai-rag-using-llamaindex",
        ["RAG", "LlamaIndex", "LLMs"],
        "A LinkedIn Learning course focused on retrieval-augmented generation using LlamaIndex.",
        format_="Video course",
        price="LinkedIn Premium",
    ),
    course(
        "Context Engineering for Developers",
        ["LinkedIn Learning Team"],
        "LinkedIn Learning",
        "https://www.linkedin.com/learning/context-engineering-for-developers",
        ["context engineering", "RAG", "AI agents", "prompt engineering"],
        "A LinkedIn Learning course for AI practitioners and prompt engineers building better AI agents and RAG pipelines.",
        format_="Video course",
        price="LinkedIn Premium",
    ),
    course(
        "Creating Agents with Python and the AI Toolkit for Visual Studio Code",
        ["LinkedIn Learning Team"],
        "LinkedIn Learning",
        "https://www.linkedin.com/learning/creating-agents-with-python-and-the-ai-toolkit-for-visual-studio-code",
        ["AI agents", "AI coding", "Python", "AI safety and evaluation"],
        "A LinkedIn Learning course on building and evaluating Python-based AI agents with the AI Toolkit for Visual Studio Code.",
        format_="Video course",
        price="LinkedIn Premium",
    ),
    course(
        "Fine-Tuning for LLMs: from Beginner to Advanced",
        ["LinkedIn Learning Team"],
        "LinkedIn Learning",
        "https://www.linkedin.com/learning/fine-tuning-for-llms-from-beginner-to-advanced",
        ["fine-tuning", "LLMs"],
        "A LinkedIn Learning course on fine-tuning LLMs from beginner to advanced level.",
        duration="3h 25m",
        format_="Video course",
        price="LinkedIn Premium",
    ),
    course(
        "Multimodal AI Essentials: Merging Text, Image, and Audio",
        ["LinkedIn Learning Team"],
        "LinkedIn Learning",
        "https://www.linkedin.com/learning/multimodal-ai-essentials-merging-text-image-and-audio-for-next-generation-ai-applications",
        ["multimodal AI", "image generation", "voice AI", "video generation"],
        "A LinkedIn Learning course on combining text, audio, video, and images for next-generation AI applications.",
        format_="Video course",
        price="LinkedIn Premium",
    ),
    course(
        "ElevenLabs: AI Voice Cloning, Text-to-Speech, and Sound Effects",
        ["LinkedIn Learning Team"],
        "LinkedIn Learning",
        "https://www.linkedin.com/learning/elevenlabs-ai-voice-cloning-text-to-speech-and-sound-effects",
        ["voice AI", "text-to-speech", "voice cloning", "audio AI"],
        "A LinkedIn Learning course exploring voice cloning, synthetic speech, and sound effects with ElevenLabs.",
        format_="Video course",
        price="LinkedIn Premium",
    ),
    course(
        "Full AI Prompting Course with Andrew Ng",
        ["Andrew Ng"],
        "YouTube",
        "https://www.youtube.com/watch?v=8ib4Qnh2HFE",
        ["prompt engineering", "LLMs", "generative AI"],
        "A YouTube course-style resource from Andrew Ng on becoming an AI power user through prompting.",
        format_="Video course",
        price="Free",
        content_type="video",
        entity_type="teaching resource",
    ),
    course(
        "Generative AI for Beginners Full Series",
        ["Microsoft"],
        "YouTube",
        "https://www.youtube.com/watch?v=k7HaeJs-N-o",
        ["LLMs", "prompt engineering", "RAG", "AI safety and evaluation"],
        "A YouTube full-series resource for Microsoft's Generative AI for Beginners, with sections on responsible AI and prompt engineering.",
        format_="Video series",
        price="Free",
        citations=["https://github.com/microsoft/generative-ai-for-beginners"],
        content_type="video",
        entity_type="teaching resource",
    ),
    course(
        "AI Agents Tutorial For Beginners",
        ["Edureka"],
        "YouTube",
        "https://www.youtube.com/watch?v=-rUKr8JDits",
        ["AI agents", "agentic AI", "LLMs"],
        "An Edureka YouTube tutorial/course for beginner AI agents and agentic AI.",
        format_="Video course",
        price="Free",
        content_type="video",
        entity_type="teaching resource",
    ),
    course(
        "GenAI Essentials - Full Course for Beginners",
        ["ExamPro"],
        "YouTube",
        "https://www.youtube.com/watch?v=nJ25yl34Uqw",
        ["LLMs", "prompt engineering", "generative AI", "cloud AI"],
        "A beginner full course on essentials of working with generative AI in the cloud.",
        format_="Video course",
        price="Free",
        content_type="video",
        entity_type="teaching resource",
    ),
    course(
        "Generative AI and LLMs Full Course 2026",
        ["Simplilearn"],
        "YouTube",
        "https://www.youtube.com/watch?v=Ru2jEY4pd7k",
        ["LLMs", "AI agents", "prompt engineering", "generative AI"],
        "A Simplilearn YouTube course covering GenAI concepts, models, agents, and tools.",
        format_="Video course",
        price="Free",
        content_type="video",
        entity_type="teaching resource",
    ),
    course(
        "Voice AI and Voice Agents 2025 - Session 01",
        ["Voice AI community instructors"],
        "YouTube",
        "https://www.youtube.com/watch?v=m4QF78X7t9k",
        ["voice AI", "AI agents", "speech-to-text", "text-to-speech"],
        "A YouTube session from a community-hosted course about building voice agents.",
        format_="Video session",
        price="Free",
        content_type="video",
        entity_type="teaching resource",
    ),
    course(
        "AI Voice Agents Full Course 2026: Beginner to Advanced",
        ["YouTube creator"],
        "YouTube",
        "https://www.youtube.com/watch?v=UAxKs9Yuljo",
        ["voice AI", "AI agents", "AI automation"],
        "A YouTube full-course style resource on AI voice agents from beginner to advanced.",
        format_="Video course",
        price="Free",
        content_type="video",
        entity_type="teaching resource",
    ),
    course(
        "Neural Networks: Zero to Hero",
        ["Andrej Karpathy"],
        "YouTube",
        "https://karpathy.ai/zero-to-hero.html",
        ["LLMs", "deep learning", "neural networks", "AI coding"],
        "A public video series on building neural networks from scratch, from backpropagation to modern deep learning.",
        format_="Video series",
        price="Free",
        citations=["https://www.youtube.com/andrejkarpathy"],
        content_type="video",
        entity_type="teaching resource",
    ),
    course(
        "Practical Deep Learning for Coders",
        ["Jeremy Howard"],
        "fast.ai",
        "https://course.fast.ai/",
        ["LLMs", "image generation", "deep learning", "AI coding"],
        "A free fast.ai course for coders learning practical deep learning.",
        syllabus=["Nine lessons", "Practical model building", "Deep learning foundations", "Stable diffusion foundations"],
        duration="9 lessons, about 90 minutes each",
        format_="Video course with notebooks",
        price="Free",
        organization="fast.ai",
    ),
    course(
        "Beginner: Introduction to Generative AI",
        ["Google Cloud"],
        "Google Skills",
        "https://www.skills.google/paths/118",
        ["LLMs", "prompt engineering", "AI safety and evaluation", "business AI"],
        "A Google Skills learning path covering generative AI concepts, LLM fundamentals, and responsible AI principles.",
        syllabus=[
            "Introduction to Generative AI",
            "Introduction to Large Language Models",
            "Introduction to Responsible AI",
            "Prompt Design in Agent Platform",
            "Responsible AI: Applying AI Principles with Google Cloud",
        ],
        audience=["Beginners", "Google Cloud partners"],
        format_="Learning path",
        organization="Google Cloud",
        entity_type="teaching resource",
    ),
    course(
        "Prompt Design in Agent Platform",
        ["Google Cloud"],
        "Google Skills",
        "https://www.skills.google/course_templates/976",
        ["prompt engineering", "multimodal AI", "image analysis", "AI agents"],
        "A Google Skills badge on prompt engineering, image analysis, and multimodal generative techniques in Agent Platform.",
        syllabus=[
            "Design prompts in Agent Platform",
            "Get started with Agent Studio",
            "Getting started with Google Generative AI using the Gen AI SDK",
            "Prompt Design in Agent Platform challenge lab",
        ],
        audience=["Beginners"],
        duration="1 hour",
        format_="Skill badge",
        certificate="Skill badge",
        organization="Google Skills",
    ),
    course(
        "Introduction to Generative AI",
        ["Google Cloud"],
        "Coursera",
        "https://www.coursera.org/learn/introduction-to-generative-ai",
        ["LLMs", "generative AI", "business AI"],
        "A Google Cloud Coursera microlearning course explaining what generative AI is, how it is used, and how it differs from traditional ML.",
        format_="Course",
        organization="Google Cloud",
        citations=["https://www.skills.google/paths/118/course_templates/536"],
    ),
    course(
        "Applied Generative AI Engineering",
        ["Udacity"],
        "Udacity",
        "https://www.udacity.com/course/generative-ai--nd608",
        ["prompt engineering", "RAG", "fine-tuning", "AI agents", "AI coding"],
        "A Udacity course on adapting foundation models using prompt engineering, RAG, fine-tuning, model compression, and agentic AI tools.",
        format_="Online course",
        organization="Udacity",
    ),
    course(
        "Generative AI and Prompt Engineering",
        ["Coursera instructors"],
        "Coursera",
        "https://www.coursera.org/learn/generative-ai--prompt-engineering",
        ["prompt engineering", "LLMs", "generative AI"],
        "A Coursera course providing foundational knowledge of generative AI concepts, foundation models, and prompt engineering techniques.",
        format_="Course",
        organization="Coursera",
    ),
    course(
        "LLM Engineering: Prompting, Fine-Tuning, Optimization and RAG",
        ["Coursera instructors"],
        "Coursera",
        "https://www.coursera.org/specializations/llm-engineering-prompting-fine-tuning-optimization-rag",
        ["LLMs", "prompt engineering", "fine-tuning", "RAG", "AI safety and evaluation"],
        "A Coursera specialization on end-to-end LLM engineering, prompt design, evaluation, fine-tuning, optimization, and RAG.",
        format_="Specialization",
        organization="Coursera",
    ),
    course(
        "Introduction to Generative AI and Agents",
        ["Microsoft"],
        "Microsoft Learn",
        "https://learn.microsoft.com/en-us/training/modules/fundamentals-generative-ai/",
        ["LLMs", "AI agents", "prompt engineering", "Azure"],
        "A Microsoft Learn module on generative AI fundamentals, LLMs, prompts, and AI agents.",
        format_="Learning module",
        price="Free",
        organization="Microsoft",
    ),
    course(
        "Get Started with AI Applications and Agents on Azure",
        ["Microsoft"],
        "Microsoft Learn",
        "https://learn.microsoft.com/en-us/training/paths/get-started-ai-apps-agents/",
        ["AI agents", "AI coding", "AI product development", "Azure"],
        "A Microsoft Learn path on building generative AI applications and agents on Azure.",
        format_="Learning path",
        price="Free",
        organization="Microsoft",
    ),
    course(
        "AI Strategy for Business Leaders",
        ["Harvard DCE"],
        "Harvard DCE",
        "https://professional.dce.harvard.edu/programs/ai-strategy-for-business-leaders/",
        ["business AI", "AI strategy", "AI product development"],
        "A Harvard Division of Continuing Education program on aligning AI with business strategy and leading AI transformation.",
        format_="Executive program",
        organization="Harvard DCE",
    ),
    course(
        "Artificial Intelligence: Implications for Business Strategy",
        ["MIT Sloan"],
        "MIT Sloan Executive Education",
        "https://executive.mit.edu/course/artificial-intelligence/a056g00000URaa3AAD.html",
        ["business AI", "AI strategy", "machine learning"],
        "A six-week MIT Sloan Executive Education online program on AI technologies and strategic business applications.",
        duration="6 weeks",
        format_="Online program",
        organization="MIT Sloan Executive Education",
    ),
    course(
        "Operationalizing No-Code AI with Zapier",
        ["Coursera instructors"],
        "Coursera",
        "https://www.coursera.org/learn/operationalizing-no-code-ai-with-zapier-automation-and-plans",
        ["no-code AI", "AI automation", "Zapier", "workflow automation"],
        "A Coursera course on designing, building, optimizing, and scaling no-code AI workflows with Zapier.",
        format_="Course",
        organization="Coursera",
    ),
    course(
        "Runway AI Video Creation",
        ["Runway Academy"],
        "Runway Academy",
        "https://academy.runwayml.com/",
        ["video generation", "multimodal AI", "generative media"],
        "Runway Academy tutorials for AI-powered video creation and generative media tools.",
        format_="Online tutorials",
        price="Free tutorials available",
        organization="Runway",
        content_type="website",
        entity_type="teaching resource",
    ),
    course(
        "Midjourney: Generative AI for Creatives Specialization",
        ["Arnold Trinh"],
        "Coursera",
        "https://www.coursera.org/specializations/midjourney-generative-ai-for-creatives",
        ["image generation", "prompt engineering", "creative AI"],
        "A Coursera specialization focused on Midjourney and generative AI for creatives.",
        format_="Specialization",
        organization="Coursera",
    ),
    course(
        "Vector Databases for Embeddings with Pinecone",
        ["DataCamp Team"],
        "DataCamp",
        "https://www.datacamp.com/courses/vector-databases-for-embeddings-with-pinecone",
        ["RAG", "vector databases", "embeddings"],
        "A DataCamp course on using Pinecone to store, manipulate, and query embedding vectors.",
        format_="Interactive course",
        price="DataCamp subscription",
        organization="DataCamp",
    ),
    course(
        "Trustworthy AI: Managing Bias, Ethics, and Accountability",
        ["Coursera instructors"],
        "Coursera",
        "https://www.coursera.org/learn/responsible-ai-and-ethics",
        ["AI safety and evaluation", "responsible AI", "AI ethics"],
        "A Coursera course on ethical, social, and technical aspects of AI and machine learning.",
        format_="Course",
        organization="Coursera",
    ),
    course(
        "AI Ethics",
        ["DataCamp Team"],
        "DataCamp",
        "https://www.datacamp.com/courses/ai-ethics",
        ["AI safety and evaluation", "AI ethics", "responsible AI"],
        "A DataCamp course covering ethical considerations in artificial intelligence.",
        format_="Interactive course",
        price="DataCamp subscription",
        organization="DataCamp",
    ),
    course(
        "11 Workshops to Build Production AI Agents",
        ["Alexey Grigorev"],
        "Substack",
        "https://alexeyondata.substack.com/p/11-workshops-to-build-production",
        ["AI agents", "RAG", "MCP", "AI safety and evaluation", "AI coding"],
        "A Substack teaching-resource post collecting GenAI workshops on agents, RAG, MCP, guardrails, and production systems.",
        format_="Newsletter post / workshop collection",
        content_type="article",
        entity_type="teaching resource",
    ),
    course(
        "The AI Engineering Course I Wish I Had",
        ["Miguel Otero Pedrido"],
        "Substack",
        "https://theneuralmaze.substack.com/p/the-ai-engineering-course-i-wish",
        ["AI agents", "MCP", "AI engineering", "AI safety and evaluation"],
        "A Substack AI engineering learning resource about MCPs, agent monitoring, and real AI systems.",
        format_="Newsletter post",
        content_type="article",
        entity_type="teaching resource",
    ),
    course(
        "Best Practices in Prompt Engineering",
        ["Sophia Yang"],
        "Medium",
        "https://medium.com/data-science/best-practices-in-prompt-engineering-a18d6bab904b",
        ["prompt engineering", "LLMs"],
        "A Medium teaching article on prompt-engineering principles, iterative development, and prompting capabilities.",
        format_="Article",
        content_type="article",
        entity_type="teaching resource",
    ),
    course(
        "Prompt Engineering for Generative AI - GOTO 2025 Session",
        ["James Phoenix", "Mike Taylor", "Phil Winder"],
        "YouTube",
        "https://www.youtube.com/watch?v=3a0WHZVb1Gg",
        ["prompt engineering", "LLMs", "conference"],
        "A GOTO 2025 YouTube conference/session source involving authors and practitioners of prompt engineering for generative AI.",
        format_="Conference session",
        content_type="interview",
        entity_type="teaching resource",
    ),
    course(
        "Almost Timely News: AI Agents 101",
        ["Christopher S. Penn"],
        "Substack",
        "https://almosttimely.substack.com/p/almost-timely-news-ai-agents-101",
        ["AI agents", "business AI", "AI automation"],
        "A Substack newsletter resource introducing AI agents and business use of generative AI.",
        format_="Newsletter post",
        content_type="article",
        entity_type="newsletter",
    ),
]


INSTRUCTOR_OVERRIDES = {
    "Aishwarya Srinivasan": {
        "headline": "AI Entrepreneur; founder at The Gen Academy; ex-Google, Microsoft, IBM",
        "organization": "The Gen Academy",
        "bio": "AI entrepreneur and founder at The Gen Academy with cited experience at Google, Microsoft, IBM, and Fireworks AI.",
        "social_profiles": {"linkedin": "https://www.linkedin.com/in/aishwarya-srinivasan/", "youtube": None, "x": None, "github": None, "other": []},
        "credibility_signals": ["Ex-Google", "Ex-Microsoft", "Founder at The Gen Academy"],
    },
    "Arvind Narayanamurthy": {
        "headline": "AI Engineering Lead; founder at The Gen Academy; AI solutions architect",
        "organization": "The Gen Academy",
        "bio": "AI engineering lead and founder at The Gen Academy with cited experience at Adobe, Microsoft, and IBM.",
        "credibility_signals": ["Founder at The Gen Academy", "Ex-Adobe", "Ex-Microsoft", "Ex-IBM"],
    },
    "Alexey Grigorev": {
        "headline": "Founder of DataTalks.Club; creator of Zoomcamp series",
        "organization": "DataTalks.Club",
        "bio": "Founder of DataTalks.Club and educator cited by Maven as teaching AI and data to 100k+ students.",
        "credibility_signals": ["Teaching AI and data to 100k+ students", "DataTalks.Club founder"],
    },
    "Jason Liu": {
        "headline": "AI consultant and creator of the Instructor Python library",
        "organization": None,
        "bio": "Machine learning engineer and consultant focused on search, recommendation, and RAG systems.",
        "credibility_signals": ["Creator of Instructor Python library", "RAG consultant"],
    },
    "Nirant Kasliwal": {
        "headline": "AI engineer; founder of FastEmbed",
        "organization": None,
        "bio": "AI engineer cited for work on chatbots, language models, vector databases, and FastEmbed.",
        "credibility_signals": ["Founder of FastEmbed"],
    },
    "Jithin James": {
        "headline": "Founder of Exploding Gradients; creator of Ragas",
        "organization": "Exploding Gradients",
        "bio": "Builder of tools for developers working with LLMs and RAG pipelines, including Ragas.",
        "credibility_signals": ["Creator of Ragas"],
    },
    "Dhruv Anand": {
        "headline": "Founder and CEO of AI Northstar Tech",
        "organization": "AI Northstar Tech",
        "bio": "Founder focused on LLMs, vector embeddings, databases, search, recommendations, and custom RAG applications.",
        "credibility_signals": ["Founder and CEO of AI Northstar Tech"],
    },
    "Hamel Husain": {
        "headline": "ML engineer and independent consultant",
        "organization": "Independent Consultant",
        "bio": "ML engineer cited by Maven with more than 25 years of experience and work with companies including Airbnb and GitHub.",
        "social_profiles": {"linkedin": "https://www.linkedin.com/in/hamelhusain/", "youtube": None, "x": None, "github": None, "other": []},
        "credibility_signals": ["Former Airbnb", "Former GitHub", "Independent AI product consultant"],
    },
    "Shreya Shankar": {
        "headline": "ML systems researcher focused on AI evaluation",
        "organization": "Carnegie Mellon University",
        "bio": "ML systems researcher working on AI-powered data processing and practical AI evaluation.",
        "social_profiles": {"linkedin": None, "youtube": None, "x": None, "github": None, "other": ["https://www.sh-reya.com/"]},
        "credibility_signals": ["PhD in Computer Science from UC Berkeley", "Assistant Professor role at Carnegie Mellon University cited by Maven"],
    },
    "John Hwang": {
        "headline": "Founder, Enterprise AI Trends; ex-AWS AI and Alexa PM",
        "organization": "Enterprise AI Trends",
        "bio": "Founder of Enterprise AI Trends and former AWS generative AI architect, according to the Maven course page.",
        "social_profiles": {"linkedin": "https://www.linkedin.com/in/jhwangj/", "youtube": None, "x": None, "github": None, "other": ["https://nextword.substack.com/"]},
        "credibility_signals": ["Ex-AWS AI", "Former Alexa PM", "Stanford CS"],
    },
    "Andrew Ng": {
        "headline": "Founder of DeepLearning.AI and Coursera co-founder",
        "organization": "DeepLearning.AI",
        "bio": "AI educator associated with DeepLearning.AI and Coursera courses in the research corpus.",
        "social_profiles": {"linkedin": None, "youtube": "https://www.youtube.com/@Deeplearningai", "x": None, "github": None, "other": ["https://www.deeplearning.ai"]},
        "credibility_signals": ["Founder of DeepLearning.AI", "Coursera co-founder"],
    },
    "Andrej Karpathy": {
        "headline": "AI educator and creator of Neural Networks: Zero to Hero",
        "organization": "Independent",
        "bio": "AI educator with public teaching resources including Neural Networks: Zero to Hero.",
        "social_profiles": {"linkedin": None, "youtube": "https://www.youtube.com/andrejkarpathy", "x": None, "github": "https://github.com/karpathy", "other": ["https://karpathy.ai"]},
        "credibility_signals": ["Creator of Neural Networks: Zero to Hero"],
    },
    "Jeremy Howard": {
        "headline": "Co-founder of fast.ai",
        "organization": "fast.ai",
        "bio": "Educator associated with fast.ai's Practical Deep Learning for Coders.",
        "social_profiles": {"linkedin": None, "youtube": "https://www.youtube.com/@howardjeremyp", "x": None, "github": None, "other": ["https://www.fast.ai"]},
        "credibility_signals": ["fast.ai co-founder"],
    },
    "Bilawal Sidhu": {
        "headline": "Generative AI creator and Maven instructor",
        "organization": None,
        "bio": "Instructor of a Maven masterclass on multimodal generative AI creation workflows.",
        "credibility_signals": ["Maven generative AI creation instructor"],
    },
}


def infer_audience_levels(courses):
    text = " ".join(" ".join(c.get("target_audience", [])) + " " + c.get("description", "") for c in courses).lower()
    levels = []
    if any(word in text for word in ["beginner", "novice", "introductory", "students"]):
        levels.append("beginner")
    if any(word in text for word in ["engineer", "developer", "product manager", "data scientist", "builder", "intermediate"]):
        levels.append("intermediate")
    if any(word in text for word in ["senior", "advanced", "production", "architect", "technical leader"]):
        levels.append("advanced")
    if any(word in text for word in ["enterprise", "leader", "executive", "cto", "business"]):
        levels.append("enterprise")
    return levels or ["intermediate"]


def instructor_summaries(courses):
    by_name = defaultdict(list)
    for c in courses:
        for name in c["instructor_names"]:
            by_name[name].append(c)

    summaries = []
    for name in sorted(by_name):
        related = by_name[name]
        override = INSTRUCTOR_OVERRIDES.get(name, {})
        citations = uniq([url for c in related for url in c["citations"]])
        tags = uniq([tag for c in related for tag in c["topic_tags"]])
        platforms = uniq([c["platform"] for c in related])
        organizations = uniq([c.get("organization") for c in related if c.get("organization")])
        social = {"linkedin": None, "youtube": None, "x": None, "github": None, "other": []}
        social.update(override.get("social_profiles", {}))
        summary = {
            "name": name,
            "slug": slugify(name),
            "headline": override.get("headline"),
            "organization": override.get("organization") if "organization" in override else (organizations[0] if len(organizations) == 1 else None),
            "bio": override.get("bio"),
            "expertise_areas": tags,
            "topics_taught": tags,
            "platforms": platforms,
            "website": override.get("website"),
            "social_profiles": social,
            "audience_levels": infer_audience_levels(related),
            "teaching_formats": uniq([c["format"] for c in related if c.get("format")]),
            "courses": [
                {
                    "course_name": c["course_name"],
                    "course_slug": c["course_slug"],
                    "platform": c["platform"],
                    "url": c["course_url"],
                    "citations": c["citations"],
                }
                for c in related
            ],
            "credibility_signals": override.get("credibility_signals", []),
            "citations": citations,
            "source_records": uniq([r for c in related for r in c["source_records"]]),
            "last_researched_at": LAST_RESEARCHED_AT,
        }
        summaries.append(summary)
    return summaries


def topic_matches(topic, c):
    haystack = " ".join([c["course_name"], c["description"]] + c["topic_tags"]).lower()
    return any(keyword.lower() in haystack for keyword in topic["keywords"])


def topic_summaries(topics, courses, instructors):
    instructors_by_name = {i["name"]: i for i in instructors}
    out = []
    for topic in topics:
        matched_courses = [c for c in courses if topic_matches(topic, c)]
        instructor_names = uniq([name for c in matched_courses for name in c["instructor_names"]])
        sources = uniq(topic["sources"] + [url for c in matched_courses for url in c["citations"]])
        out.append(
            {
                "topic": topic["topic"],
                "slug": slugify(topic["topic"]),
                "description": topic["description"],
                "related_topics": topic["related_topics"],
                "instructors": [
                    {
                        "name": name,
                        "slug": slugify(name),
                        "relevance": "Associated with cited courses or teaching resources for this topic.",
                        "platforms": instructors_by_name.get(name, {}).get("platforms", []),
                        "citations": instructors_by_name.get(name, {}).get("citations", []),
                    }
                    for name in instructor_names
                ],
                "courses": [
                    {
                        "course_name": c["course_name"],
                        "course_slug": c["course_slug"],
                        "instructor_names": c["instructor_names"],
                        "platform": c["platform"],
                        "course_url": c["course_url"],
                        "citations": c["citations"],
                    }
                    for c in matched_courses
                ],
                "sources": sources,
                "last_researched_at": LAST_RESEARCHED_AT,
            }
        )
    return out


def course_summary(c):
    return {
        "course_name": c["course_name"],
        "course_slug": c["course_slug"],
        "instructor_names": c["instructor_names"],
        "instructor_slugs": [slugify(name) for name in c["instructor_names"]],
        "platform": c["platform"],
        "course_url": c["course_url"],
        "topic_tags": c["topic_tags"],
        "description": c["description"],
        "syllabus": c["syllabus"],
        "target_audience": c["target_audience"],
        "prerequisites": c["prerequisites"],
        "duration": c["duration"],
        "format": c["format"],
        "price": parse_price(c["price_raw"]),
        "rating": parse_rating(c["rating_raw"]),
        "certificate": c["certificate"],
        "enrollment_status": c["enrollment_status"],
        "last_updated": c["last_updated"],
        "citations": c["citations"],
        "source_records": c["source_records"],
        "last_researched_at": LAST_RESEARCHED_AT,
    }


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def platform_results_payload(entity_type, entity_name, entity_slug, platform, query_terms, records):
    return {
        "entity_type": entity_type,
        "entity_name": entity_name,
        "entity_slug": entity_slug,
        "platform": platform,
        "query_terms": query_terms,
        "results": [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "content_type": r.get("content_type", "other"),
                "summary": r.get("summary"),
                "extracted_data": r.get("extracted_data", {}),
                "citations": r.get("citations") or ([r["url"]] if r.get("url") else []),
            }
            for r in records
        ],
        "last_researched_at": LAST_RESEARCHED_AT,
    }


def write_platform_results(entity_dir, entity_type, entity_name, entity_slug, records, query_terms):
    grouped = defaultdict(list)
    for r in records:
        grouped[platform_folder(r.get("platform"), r.get("url"))].append(r)
    for folder, recs in grouped.items():
        if folder not in PLATFORM_FOLDERS:
            folder = "other"
        write_json(
            entity_dir / folder / "results.json",
            platform_results_payload(entity_type, entity_name, entity_slug, folder, query_terms, recs),
        )


def main():
    for required in ["topics", "instructors", "courses"]:
        (BASE / required).mkdir(parents=True, exist_ok=True)

    courses = []
    seen_urls = {}
    for c in COURSES:
        key = c["course_url"]
        if key in seen_urls:
            existing = courses[seen_urls[key]]
            existing["citations"] = uniq(existing["citations"] + c["citations"])
            existing["topic_tags"] = uniq(existing["topic_tags"] + c["topic_tags"])
            existing["source_records"] = uniq(existing["source_records"] + c["source_records"])
        else:
            seen_urls[key] = len(courses)
            courses.append(c)

    instructors = instructor_summaries(courses)
    topics = topic_summaries(TOPICS, courses, instructors)

    for c in courses:
        entity_dir = BASE / "courses" / c["course_slug"]
        write_json(entity_dir / "course_summary.json", course_summary(c))
        write_platform_results(entity_dir, "course", c["course_name"], c["course_slug"], c["source_records"], [c["course_name"]] + c["topic_tags"])

    for i in instructors:
        entity_dir = BASE / "instructors" / i["slug"]
        write_json(entity_dir / "instructor_summary.json", i)
        write_platform_results(entity_dir, "instructor", i["name"], i["slug"], i["source_records"], [i["name"]] + i["expertise_areas"])

    courses_by_slug = {c["course_slug"]: c for c in courses}
    for t in topics:
        entity_dir = BASE / "topics" / t["slug"]
        write_json(entity_dir / "topic_summary.json", t)
        records = []
        for c_ref in t["courses"]:
            records.extend(courses_by_slug[c_ref["course_slug"]]["source_records"])
        for src in t["sources"]:
            records.append(record(platform_folder(url=src), src, f"Source for {t['topic']}", f"Citation source for {t['topic']}.", "other"))
        write_platform_results(entity_dir, "topic", t["topic"], t["slug"], uniq(records), [t["topic"]] + t["related_topics"])

    source_urls = sorted(uniq([url for c in courses for url in c["citations"]] + [url for t in TOPICS for url in t["sources"]]))
    platform_counts = Counter(platform_folder(c["platform"], c["course_url"]) for c in courses)
    organization_counts = Counter(c.get("organization") for c in courses if c.get("organization"))

    index = {
        "generated_at": LAST_RESEARCHED_AT,
        "base_directory": str(BASE),
        "counts": {
            "topics": len(topics),
            "instructors": len(instructors),
            "courses_and_teaching_resources": len(courses),
            "source_urls": len(source_urls),
            "platforms": len(platform_counts),
        },
        "topics": [
            {"topic": t["topic"], "slug": t["slug"], "path": f"topics/{t['slug']}/topic_summary.json", "source_count": len(t["sources"])}
            for t in topics
        ],
        "instructors": [
            {
                "name": i["name"],
                "slug": i["slug"],
                "path": f"instructors/{i['slug']}/instructor_summary.json",
                "platforms": i["platforms"],
                "course_count": len(i["courses"]),
                "citations": i["citations"],
            }
            for i in instructors
        ],
        "courses": [
            {
                "course_name": c["course_name"],
                "course_slug": c["course_slug"],
                "entity_type": c["entity_type"],
                "path": f"courses/{c['course_slug']}/course_summary.json",
                "platform": c["platform"],
                "url": c["course_url"],
                "instructor_names": c["instructor_names"],
                "topic_tags": c["topic_tags"],
                "citations": c["citations"],
            }
            for c in courses
        ],
        "organizations": [
            {"name": name, "associated_record_count": count}
            for name, count in sorted(organization_counts.items())
        ],
        "source_urls": source_urls,
        "platform_counts": dict(sorted(platform_counts.items())),
        "firecrawl": {
            "capabilities_discovered": FIRECRAWL_CAPABILITIES_DISCOVERED,
            "searches_performed": SEARCHES_PERFORMED,
            "agent_job_id": "019ec7b1-a39d-7509-8f1a-dcfa2c5fc577",
            "crawl_job_id": "019ec7b3-9261-7118-b070-8f6c2d878dbe",
            "interaction_probe": {
                "scrape_id": "019ec7b6-15a5-76e3-a995-1bcd5ea318ce",
                "url": "https://huggingface.co/learn/agents-course/unit0/introduction",
                "result": "Read page title and top-level heading, then stopped the interaction session.",
            },
            "mapped_urls": [
                "https://maven.com/courses/ai/rag-search",
                "https://maven.com/courses/ai/evals",
                "https://maven.com/courses/ai/for-operators",
                "https://maven.com/courses/ai/for-marketers",
                "https://maven.com/courses/ai/vibe-coding",
                "https://maven.com/courses/ai/prototyping",
                "https://maven.com/courses/ai/claude-code",
                "https://maven.com/courses/ai/agentic-ai",
                "https://maven.com/courses/ai/ai-coding",
                "https://maven.com/courses/ai/ai-workflows",
                "https://maven.com/courses/ai/ai-transformation",
            ],
        },
    }
    write_json(BASE / "research_index.json", index)

    required_topics = [
        "LLMs",
        "prompt engineering",
        "RAG",
        "AI agents",
        "fine-tuning",
        "multimodal AI",
        "image generation",
        "video generation",
        "voice AI",
        "AI coding",
        "AI product development",
        "AI automation",
        "business AI",
        "no-code AI",
        "AI safety and evaluation",
    ]
    topic_by_name = {t["topic"]: t for t in topics}
    coverage = {
        "generated_at": LAST_RESEARCHED_AT,
        "summary": "Local research corpus built from Firecrawl search, scrape, extract, map, crawl, and agent outputs. Unknown or unsupported fields are null rather than invented.",
        "counts": index["counts"],
        "required_topic_coverage": [
            {
                "topic": name,
                "covered": name in topic_by_name,
                "course_count": len(topic_by_name.get(name, {}).get("courses", [])),
                "instructor_count": len(topic_by_name.get(name, {}).get("instructors", [])),
                "source_count": len(topic_by_name.get(name, {}).get("sources", [])),
            }
            for name in required_topics
        ],
        "additional_topics_discovered": [t["topic"] for t in topics if t["topic"] not in required_topics],
        "platforms_covered": dict(sorted(platform_counts.items())),
        "firecrawl_workflow": {
            "capability_discovery": "Used tool discovery for Firecrawl tools before research.",
            "search": f"{len(SEARCHES_PERFORMED)} Firecrawl searches with feedback submitted for each search.",
            "scrape": "Structured JSON scrapes were used for selected Maven and Hugging Face pages.",
            "extract": "Batch extraction was used for Maven, DeepLearning.AI, Google Skills, media-generation, and voice-agent pages.",
            "map": "Mapped Maven AI catalog to discover category and course URLs.",
            "crawl": "Crawled Maven AI catalog with summary and links extraction; status checked after crawl.",
            "agent": "Firecrawl autonomous agent completed broad cross-source discovery and enrichment.",
            "interaction": "Used firecrawl_interact on the scraped Hugging Face Agents Course page to verify the live title and heading, then used firecrawl_interact_stop to close the session.",
            "monitors": "Monitor tools were discovered but not used because the task requested a point-in-time corpus, not recurring change tracking.",
        },
        "known_limitations": [
            "LinkedIn direct scraping was blocked by Firecrawl for linkedin.com; LinkedIn records are retained from Firecrawl search snippets and cited URLs, with unavailable fields null.",
            "The corpus is broad and citation-backed, but public web search is not a mathematically exhaustive crawl of every possible course marketplace, video, post, or private platform.",
            "Some YouTube, LinkedIn, Coursera, and marketplace records rely on search result metadata when full page extraction was unavailable or unnecessary for sparse teaching-resource records.",
            "Instructor profiles are strongest for pages that exposed bios during extraction; otherwise the profile keeps unknown fields null and relies on course associations.",
            "Prices, enrollment status, and cohort dates can change after this timestamp.",
        ],
        "unsupported_or_blocked_sources": [
            {
                "url": "https://www.linkedin.com/learning/introduction-to-prompt-engineering-for-generative-ai-24636124",
                "tool": "firecrawl_scrape",
                "result": "Firecrawl reported that the site is unsupported.",
            }
        ],
        "source_quality_notes": [
            "Primary sources were preferred for course summaries: Maven, Hugging Face, DeepLearning.AI, Google Skills, LinkedIn Learning, Microsoft Learn, GitHub repositories, and official course pages.",
            "Secondary sources such as Class Central, Medium, Substack, and YouTube sessions are preserved as corroborating or teaching-resource records.",
            "Every generated entity summary includes URL citations.",
        ],
    }
    write_json(BASE / "coverage_report.json", coverage)


if __name__ == "__main__":
    main()
